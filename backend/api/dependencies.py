from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.db_models import User, Workspace
from backend.security import decode_access_token

bearer = HTTPBearer(auto_error=False)

@dataclass
class Identity:
    user: User | None
    guest_id: str | None

def get_identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 x_guest_id: str | None = Header(default=None),
                 db: Session = Depends(get_db)) -> Identity:
    if credentials:
        uid = decode_access_token(credentials.credentials)
        user = db.get(User, uid) if uid else None
        if not user or not user.is_active:
            raise HTTPException(401, "Invalid or expired token")
        return Identity(user=user, guest_id=None)
    return Identity(user=None, guest_id=x_guest_id.strip() if x_guest_id else None)

def require_user(identity: Identity = Depends(get_identity)) -> User:
    if not identity.user:
        raise HTTPException(401, "Authentication required")
    return identity.user

def authorize_workspace(workspace: Workspace, identity: Identity):
    ok = (identity.user and workspace.user_id == identity.user.id) or (
        not identity.user and identity.guest_id and workspace.guest_id == identity.guest_id
    )
    if not ok:
        raise HTTPException(404, "Workspace not found")
