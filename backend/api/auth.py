from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.database import get_db
from backend.models.db_models import User
from backend.models.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.repositories.user_repo import (
    create_user,
    get_user_by_email,
)
from backend.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    if get_user_by_email(db=db, email=payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    try:
        user = create_user(
            db=db,
            email=payload.email,
            password_hash=hash_password(payload.password),
        )

    except IntegrityError as exc:
        # Two simultaneous registrations for the same email:
        # the UNIQUE constraint on users.email is the final guard.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db=db, email=payload.email)

    if user is None:
        # Same work as a real check, so timing doesn't reveal
        # whether the email exists.
        verify_password(payload.password, DUMMY_PASSWORD_HASH)
        password_ok = False
    else:
        password_ok = verify_password(
            payload.password,
            user.password_hash,
        )

    if user is None or not password_ok:
        # Identical message for "no such email" and "wrong password".
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user
