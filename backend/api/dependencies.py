from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.orm import object_session
from backend.database import get_db
from backend.models.db_models import User, Workspace, GuestSession, AuthSession
from backend.security import decode_session_token, token_hash
from backend.services.rate_limit import limit
from backend.config import settings

bearer = HTTPBearer(auto_error=False)

@dataclass
class Identity:
    user: User | None
    guest_id: str | None
    session_id: object | None = None
    expires_at: datetime | None = None

def get_identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 x_guest_id: str | None = Header(default=None),
                 db: Session = Depends(get_db)) -> Identity:
    if credentials:
        decoded = decode_session_token(credentials.credentials)
        session = db.get(AuthSession, decoded[1]) if decoded else None
        user = db.get(User, decoded[0]) if decoded else None
        if not user or not user.is_active or not session or session.user_id!=user.id or session.revoked or session.expires_at<=datetime.now(timezone.utc):
            raise HTTPException(401, "Invalid or expired token")
        return Identity(user=user, guest_id=None,session_id=session.id,expires_at=session.expires_at)
    if x_guest_id:
        digest=token_hash(x_guest_id.strip())
        guest=db.get(GuestSession,digest)
        if not guest or guest.claimed or guest.expires_at<=datetime.now(timezone.utc):
            raise HTTPException(401,"Guest session is invalid or expired")
        limit(db,"guest-requests",digest,settings.GUEST_MAX_REQUESTS)
        return Identity(user=None,guest_id=digest,expires_at=guest.expires_at)
    return Identity(user=None,guest_id=None)

def require_user(identity: Identity = Depends(get_identity)) -> User:
    if not identity.user:
        raise HTTPException(401, "Authentication required")
    if not identity.user.email_verified:
        raise HTTPException(403,"Verify your email before accessing workspaces")
    return identity.user

def authorize_workspace(workspace: Workspace, identity: Identity):
    if identity.expires_at and identity.expires_at<=datetime.now(timezone.utc):
        raise HTTPException(401,"Session expired")
    db=object_session(workspace)
    if db and identity.session_id:
        session=db.get(AuthSession,identity.session_id,populate_existing=True)
        if not session or session.revoked or session.expires_at<=datetime.now(timezone.utc):
            raise HTTPException(401,"Session expired or revoked")
    if db and identity.guest_id:
        guest=db.get(GuestSession,identity.guest_id,populate_existing=True)
        if not guest or guest.claimed or guest.expires_at<=datetime.now(timezone.utc):
            raise HTTPException(401,"Guest session expired")
    if identity.user and not identity.user.email_verified:
        raise HTTPException(403,"Verify your email before accessing workspaces")
    ok = (identity.user and workspace.user_id == identity.user.id) or (
        not identity.user and identity.guest_id and workspace.guest_id == identity.guest_id
    )
    if not ok:
        raise HTTPException(404, "Workspace not found")
