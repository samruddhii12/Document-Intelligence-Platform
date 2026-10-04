from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        return RegisterRequest.password_bytes(value)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    email_verified: bool

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    created_at: datetime
    email_verified: bool

class TokenRequest(BaseModel):
    token: str = Field(min_length=20,max_length=256)

class EmailRequest(BaseModel):
    email: EmailStr

class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20,max_length=256)

class GoogleExchange(BaseModel):
    code: str = Field(min_length=20,max_length=256)
    handoff_secret: str = Field(min_length=20,max_length=256)

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    document_ids: list[UUID] | None = None

class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
