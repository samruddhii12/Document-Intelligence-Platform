import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from backend.config import settings
from backend.models.db_models import AuthSession, VerificationChallenge, MailOutbox, GuestSession
from backend.security import token_hash, create_access_token


def issue_session(db,user):
    secret=secrets.token_urlsafe(48)
    session=AuthSession(user_id=user.id,refresh_hash=token_hash(secret),expires_at=datetime.now(timezone.utc)+timedelta(days=7))
    db.add(session); db.flush()
    return session_response(user,session,secret)


def session_response(user,session,secret):
    return {"access_token":create_access_token(user.id,session.id),"refresh_token":secret,"token_type":"bearer",
            "expires_in":settings.ACCESS_TOKEN_EXPIRE_MINUTES*60,"email_verified":user.email_verified}


def queue_verification(db,user):
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        raise HTTPException(503,"Email verification is not configured. Set SMTP_HOST and SMTP_FROM in .env.")
    now=datetime.now(timezone.utc)
    latest=db.query(VerificationChallenge).filter_by(user_id=user.id).order_by(VerificationChallenge.created_at.desc()).first()
    if latest and latest.created_at>now-timedelta(seconds=60):
        raise HTTPException(429,"Wait 60 seconds before requesting another verification email")
    db.query(VerificationChallenge).filter_by(user_id=user.id,consumed=False).update({"consumed":True})
    # Invalidate unsent mail when a newer challenge replaces it.
    db.query(MailOutbox).filter_by(user_id=user.id,status="queued").update({"status":"cancelled","body":""})
    token=secrets.token_urlsafe(48)
    db.add(VerificationChallenge(user_id=user.id,token_hash=token_hash(token),expires_at=now+timedelta(minutes=30)))
    link=settings.FRONTEND_URL.rstrip("/")+"/?verify="+token
    db.add(MailOutbox(user_id=user.id,recipient=user.email,subject="Verify your DocMind email",
                     body=f"Confirm your email in DocMind:\n{link}\n\nThis link expires in 30 minutes. If you did not request it, ignore this email."))


def create_guest(db):
    secret=secrets.token_urlsafe(32)
    digest=token_hash(secret)
    db.add(GuestSession(token_hash=digest,expires_at=datetime.now(timezone.utc)+timedelta(hours=settings.GUEST_TTL_HOURS)))
    db.flush()
    return secret,digest
