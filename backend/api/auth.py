import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.database import get_db
from backend.models.db_models import User, AuthSession, VerificationChallenge, GuestSession
from backend.config import settings
from backend.models.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse, EmailRequest, TokenRequest, RefreshRequest
from backend.security import hash_password, verify_password, token_hash
from backend.api.dependencies import get_identity, Identity
from backend.services.authentication import issue_session, session_response, queue_verification, create_guest
from backend.services.rate_limit import limit

router=APIRouter(prefix="/auth",tags=["auth"])

@router.get("/capabilities")
def capabilities():
    from backend.config import settings
    return {"email_verification":bool(settings.SMTP_HOST and settings.SMTP_FROM),
            "google_sign_in":bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)}

@router.post("/register",response_model=TokenResponse,status_code=201)
def register(p:RegisterRequest,request:Request,db:Session=Depends(get_db)):
    email=str(p.email).lower().strip()
    limit(db,"register",request.client.host if request.client else "unknown",10)
    if db.query(User).filter(User.email==email).first():
        raise HTTPException(409,"Email already registered. Sign in or resend verification.")
    user=User(email=email,password_hash=hash_password(p.password),email_verified=False)
    try:
        db.add(user); db.flush()
        queue_verification(db,user)
        response=issue_session(db,user)
        db.commit()
    except IntegrityError as error:
        db.rollback(); raise HTTPException(409,"Email already registered") from error
    return response

@router.post("/login",response_model=TokenResponse)
def login(p:LoginRequest,request:Request,db:Session=Depends(get_db)):
    email=str(p.email).lower().strip()
    limit(db,"login-email",email,20)
    limit(db,"login-ip",request.client.host if request.client else "unknown",100)
    user=db.query(User).filter(User.email==email).first()
    if not user or not verify_password(p.password,user.password_hash):
        raise HTTPException(401,"Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403,"Account disabled")
    response=issue_session(db,user); db.commit()
    return response

@router.get("/me",response_model=UserResponse)
def me(identity:Identity=Depends(get_identity)):
    if not identity.user:
        raise HTTPException(401,"Authentication required")
    return identity.user

@router.post("/verification/resend")
def resend(p:EmailRequest,request:Request,db:Session=Depends(get_db)):
    email=str(p.email).lower().strip()
    limit(db,"resend-email",email,5)
    limit(db,"resend-ip",request.client.host if request.client else "unknown",20)
    user=db.query(User).filter(User.email==email).with_for_update().first()
    if user and user.is_active and not user.email_verified:
        queue_verification(db,user); db.commit()
    return {"message":"If verification is needed, an email will be sent."}

@router.post("/verification/confirm")
def confirm(p:TokenRequest,request:Request,db:Session=Depends(get_db)):
    limit(db,"verify-ip",request.client.host if request.client else "unknown",30)
    challenge=db.query(VerificationChallenge).filter_by(token_hash=token_hash(p.token)).first()
    if not challenge or challenge.consumed or challenge.expires_at<=datetime.now(timezone.utc):
        raise HTTPException(400,"Verification link is invalid or expired")
    user=db.query(User).filter_by(id=challenge.user_id).with_for_update().first()
    if not user or not user.is_active:
        raise HTTPException(400,"Verification link is invalid or expired")
    challenge=db.query(VerificationChallenge).filter_by(token_hash=token_hash(p.token)).populate_existing().with_for_update().first()
    if not challenge or challenge.consumed or challenge.expires_at<=datetime.now(timezone.utc):
        raise HTTPException(400,"Verification link is invalid or expired")
    user.email_verified=True; challenge.consumed=True; db.commit()
    return {"verified":True}

@router.post("/refresh",response_model=TokenResponse)
def refresh(p:RefreshRequest,db:Session=Depends(get_db)):
    session=db.query(AuthSession).filter_by(refresh_hash=token_hash(p.refresh_token)).with_for_update().first()
    if not session or session.revoked or session.expires_at<=datetime.now(timezone.utc):
        raise HTTPException(401,"Refresh token is invalid or expired")
    user=db.get(User,session.user_id)
    if not user or not user.is_active:
        raise HTTPException(401,"Account unavailable")
    secret=secrets.token_urlsafe(48); session.refresh_hash=token_hash(secret)
    response=session_response(user,session,secret); db.commit()
    return response

@router.post("/logout")
def logout(identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    if not identity.session_id:
        raise HTTPException(401,"Authentication required")
    session=db.get(AuthSession,identity.session_id); session.revoked=True; db.commit()
    return {"logged_out":True}

@router.post("/guest",status_code=201)
def guest(request:Request,db:Session=Depends(get_db)):
    limit(db,"guest-ip",request.client.host if request.client else "unknown",20)
    secret,digest=create_guest(db); db.commit()
    return {"guest_id":secret,"expires_in_hours":settings.GUEST_TTL_HOURS}

@router.post("/guest/end")
def end_guest(identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    if not identity.guest_id: raise HTTPException(401,"Guest session required")
    guest=db.get(GuestSession,identity.guest_id); guest.expires_at=datetime.now(timezone.utc); db.commit()
    return {"ended":True}
