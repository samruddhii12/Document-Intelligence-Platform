from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.security import MAX_PASSWORD_BYTES


class UploadResponse(BaseModel):
    session_id: str
    filename: str
    # Phase 3.2: identifies the guest that owns the new workspace.
    # The client should send it back in the X-Guest-Id header on
    # later uploads so they land in the same guest identity.
    guest_id: str | None = None


# ----------------------------------------------------------------------
# Authentication (Phase 3.3 - 3.6)
# ----------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(
                f"Password must be at most {MAX_PASSWORD_BYTES} bytes"
            )
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    # No minimum length at login: just verify what was typed.
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime
