"""Pydantic models for authentication requests/responses."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TwoFactorPendingResponse(BaseModel):
    requires_2fa: bool = True
    temp_token: str


class TwoFactorVerifyRequest(BaseModel):
    temp_token: str
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str
