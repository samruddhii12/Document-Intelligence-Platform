"""
Authentication dependencies (Phase 3.6).

Use in routes:

    current_user: User = Depends(get_current_user)       # login required
    maybe_user: User | None = Depends(get_optional_user)  # login optional
                                                         # (guests, Phase 3.7+)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.db_models import User
from backend.repositories.user_repo import get_user_by_id
from backend.security import decode_access_token


# auto_error=False so we control the response and so the same scheme
# can be used for routes where a login is optional.
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User | None:
    """
    No Authorization header      -> None (anonymous / guest)
    Valid token                  -> the User
    Invalid or expired token     -> 401 (never silently treated as guest)
    """
    if credentials is None:
        return None

    user_id = decode_access_token(credentials.credentials)

    if user_id is None:
        raise _unauthorized("Invalid or expired token")

    user = get_user_by_id(db=db, user_id=user_id)

    if user is None:
        raise _unauthorized("Invalid or expired token")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


def get_current_user(
    user: User | None = Depends(get_optional_user),
) -> User:
    """
    Login required. Returns the authenticated, active user.
    """
    if user is None:
        raise _unauthorized("Not authenticated")

    return user
