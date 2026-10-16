from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=1024)


class RefreshRequest(BaseModel):
    refresh_token: SecretStr = Field(min_length=40, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: SecretStr = Field(min_length=40, max_length=512)


class AdminIdentity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    roles: list[str]
    permissions: list[str]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime
    admin: AdminIdentity


class MessageResponse(BaseModel):
    success: bool
    message: str

