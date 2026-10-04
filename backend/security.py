"""
Password hashing and JWT helpers (Phase 3.4 / 3.5).

Passwords are hashed with bcrypt. Access tokens are signed JWTs
containing the user id in the standard "sub" claim.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt

from backend.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)


# bcrypt only uses the first 72 BYTES of a password.
# We reject longer passwords instead of silently truncating them.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt (random salt included).
    """
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes"
        )

    return bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Check a plaintext password against a stored bcrypt hash.
    Never raises; returns False for anything invalid.
    """
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False

    try:
        return bcrypt.checkpw(
            password_bytes,
            password_hash.encode("utf-8"),
        )
    except ValueError:
        # Malformed hash
        return False


# Used to spend the same time verifying when the email is unknown, so
# response time doesn't reveal which emails are registered.
DUMMY_PASSWORD_HASH = hash_password("timing-attack-protection")


def create_access_token(user_id: UUID) -> str:
    """
    Create a signed JWT for a user.
    """
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> UUID | None:
    """
    Validate a JWT and return the user id it was issued for.

    Returns None if the token is malformed, tampered with, signed with
    another key, expired, or has no valid user id.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )

        return UUID(payload["sub"])

    except (jwt.PyJWTError, ValueError, TypeError):
        return None
