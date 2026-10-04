import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from urllib.parse import urlencode
import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.database import get_db
from backend.config import settings
from backend.models.db_models import OAuthAttempt, AuthIdentity, User, AuthSession
from backend.models.schemas import GoogleExchange, TokenRequest
from backend.api.dependencies import get_identity, Identity
from backend.security import token_hash
from backend.services.authentication import issue_session
from backend.services.rate_limit import limit

router=APIRouter(prefix="/auth/google",tags=["auth"])

@lru_cache(maxsize=1)
def google_keys():
    return jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs",timeout=10)

@router.post("/prepare")
def prepare(request:Request,link:bool=False,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(503,"Google Sign-In is not configured")
    if link and (not identity.user or not identity.user.email_verified):
        raise HTTPException(403,"Sign in to a verified account before linking Google")
    limit(db,"google-ip",request.client.host if request.client else "unknown",20)
    state=secrets.token_urlsafe(32); nonce=secrets.token_urlsafe(32)
    verifier=secrets.token_urlsafe(64); handoff=secrets.token_urlsafe(32)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    attempt=OAuthAttempt(state_hash=token_hash(state),nonce=nonce,verifier=verifier,handoff_hash=token_hash(handoff),
                         link_user_id=identity.user.id if link else None,link_session_id=identity.session_id if link else None,
                         expires_at=datetime.now(timezone.utc)+timedelta(minutes=10))
    db.add(attempt); db.commit()
    url="https://accounts.google.com/o/oauth2/v2/auth?"+urlencode({"client_id":settings.GOOGLE_CLIENT_ID,
        "redirect_uri":settings.PUBLIC_API_URL.rstrip("/")+"/auth/google/callback", "response_type":"code",
        "scope":"openid email profile","state":state,"nonce":nonce,"code_challenge":challenge,"code_challenge_method":"S256"})
    return {"authorization_url":url,"handoff_secret":handoff}

@router.get("/callback")
def callback(state:str="",code:str="",error:str="",db:Session=Depends(get_db)):
    # Claim the one-time state before making external calls; no DB locks during network I/O.
    attempt=db.query(OAuthAttempt).filter_by(state_hash=token_hash(state)).with_for_update().first()
    if not attempt or attempt.consumed or attempt.expires_at<=datetime.now(timezone.utc):
        raise HTTPException(400,"Google login state is invalid or expired")
    attempt.consumed=True; db.commit()
    if error or not code:
        raise HTTPException(400,"Google sign-in was cancelled or denied")
    try:
        response=requests.post("https://oauth2.googleapis.com/token",data={"client_id":settings.GOOGLE_CLIENT_ID,
            "client_secret":settings.GOOGLE_CLIENT_SECRET,"code":code,"code_verifier":attempt.verifier,
            "grant_type":"authorization_code","redirect_uri":settings.PUBLIC_API_URL.rstrip("/")+"/auth/google/callback"},timeout=(5,15))
        response.raise_for_status()
        encoded=response.json()["id_token"]
        key=google_keys().get_signing_key_from_jwt(encoded).key
        claims=jwt.decode(encoded,key,algorithms=["RS256"],audience=settings.GOOGLE_CLIENT_ID,
                          issuer=["https://accounts.google.com","accounts.google.com"],
                          options={"require":["sub","exp","iat","aud","iss","nonce"]})
        if not hmac.compare_digest(str(claims["nonce"]),attempt.nonce) or claims.get("email_verified") is not True or claims.get("azp",settings.GOOGLE_CLIENT_ID)!=settings.GOOGLE_CLIENT_ID:
            raise ValueError("Unverified identity")
        from pydantic import TypeAdapter, EmailStr
        email=str(TypeAdapter(EmailStr).validate_python(claims["email"])).lower()
    except (requests.RequestException,jwt.PyJWTError,KeyError,ValueError) as failure:
        raise HTTPException(400,"Google identity could not be verified. Start sign-in again.") from failure
    identity=db.query(AuthIdentity).filter_by(provider="google",subject=claims["sub"]).first()
    if attempt.link_user_id:
        session=db.get(AuthSession,attempt.link_session_id) if attempt.link_session_id else None
        if not session or session.revoked or session.expires_at<=datetime.now(timezone.utc):
            raise HTTPException(401,"Linking session expired. Sign in and start again.")
        user=db.get(User,attempt.link_user_id)
        if not user or not user.is_active or not user.email_verified or user.email!=email:
            raise HTTPException(409,"Google email must match your verified account")
        if identity and identity.user_id!=user.id:
            raise HTTPException(409,"Google identity is already linked to another account")
    elif identity:
        user=db.get(User,identity.user_id)
    else:
        user=db.query(User).filter_by(email=email).first()
        if user:
            raise HTTPException(409,"This email already has an account. Sign in with its password and use Link Google in Account.")
        user=User(email=email,password_hash="!google-only",email_verified=True)
        db.add(user); db.flush()
    if not user or not user.is_active:
        raise HTTPException(403,"Account unavailable")
    if not identity:
        db.add(AuthIdentity(user_id=user.id,provider="google",subject=claims["sub"]))
    handoff_code=secrets.token_urlsafe(32)
    attempt.user_id=user.id; attempt.code_hash=token_hash(handoff_code)
    attempt.expires_at=datetime.now(timezone.utc)+timedelta(minutes=2)
    attempt.verifier=""; attempt.nonce=""
    try:
        db.commit()
    except IntegrityError as failure:
        db.rollback(); raise HTTPException(409,"Account changed during login. Start again.") from failure
    return HTMLResponse("<html><body><h2>Google sign-in complete</h2><p>Return to the original DocMind tab and click Complete Google Sign-In.</p></body></html>",
                        headers={"Cache-Control":"no-store","Referrer-Policy":"no-referrer"})

@router.post("/exchange")
def exchange(p:GoogleExchange,db:Session=Depends(get_db)):
    attempt=db.query(OAuthAttempt).filter_by(code_hash=token_hash(p.code)).with_for_update().first()
    if not attempt or not attempt.code_hash or not attempt.user_id or attempt.expires_at<=datetime.now(timezone.utc) or not hmac.compare_digest(attempt.handoff_hash,token_hash(p.handoff_secret)):
        raise HTTPException(400,"Google login handoff is invalid or expired. Return to the original login tab.")
    user=db.get(User,attempt.user_id)
    if not user or not user.is_active:
        raise HTTPException(403,"Account unavailable")
    attempt.code_hash=None
    response=issue_session(db,user); db.commit()
    return response

@router.post("/complete")
def complete(p:TokenRequest,db:Session=Depends(get_db)):
    attempt=db.query(OAuthAttempt).filter_by(handoff_hash=token_hash(p.token)).with_for_update().first()
    if not attempt or attempt.expires_at<=datetime.now(timezone.utc):
        raise HTTPException(400,"Google sign-in expired. Start again.")
    if not attempt.user_id or not attempt.code_hash:
        raise HTTPException(409,"Complete Google sign-in in the new tab first")
    user=db.get(User,attempt.user_id)
    if not user or not user.is_active: raise HTTPException(403,"Account unavailable")
    attempt.code_hash=None; attempt.handoff_hash=token_hash(secrets.token_urlsafe(32))
    response=issue_session(db,user); db.commit()
    return response
