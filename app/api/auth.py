"""Authentication endpoints: login, 2FA verify, token refresh."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MCCError
from app.core.security import (
    create_2fa_temp_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    verify_totp,
)
from app.db.models import User
from app.db.session import get_db
from app.models.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    TwoFactorPendingResponse,
    TwoFactorVerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Pre-computed dummy hash so invalid-username attempts still run argon2 verify
# (prevents timing side-channel for username enumeration)
_DUMMY_HASH = hash_password("dummy")


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse | TwoFactorPendingResponse:
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    password_hash = user.password_hash if user is not None else _DUMMY_HASH
    if not verify_password(body.password, password_hash) or user is None:
        raise MCCError(
            code="INVALID_CREDENTIALS",
            message="Invalid username or password",
            status_code=401,
        )

    if not user.is_active:
        raise MCCError(code="USER_INACTIVE", message="User account is inactive", status_code=403)

    if user.is_2fa_enabled and user.totp_secret:
        temp_token = create_2fa_temp_token({"sub": str(user.id)})
        return TwoFactorPendingResponse(temp_token=temp_token)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/2fa/verify")
async def verify_2fa(
    body: TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        payload = decode_token(body.temp_token)
    except Exception as e:
        raise MCCError(
            code="INVALID_TOKEN", message="Invalid or expired 2FA token", status_code=401
        ) from e

    if payload.get("type") != "2fa_temp":
        raise MCCError(code="INVALID_TOKEN", message="Not a 2FA temp token", status_code=401)

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.totp_secret or not user.is_active:
        raise MCCError(code="INVALID_TOKEN", message="User not found", status_code=401)

    if not verify_totp(user.totp_secret, body.code):
        raise MCCError(code="INVALID_2FA_CODE", message="Invalid 2FA code", status_code=401)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except Exception as e:
        raise MCCError(
            code="INVALID_TOKEN", message="Invalid or expired refresh token", status_code=401
        ) from e

    if payload.get("type") != "refresh":
        raise MCCError(code="INVALID_TOKEN", message="Not a refresh token", status_code=401)

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise MCCError(code="INVALID_TOKEN", message="User not found or inactive", status_code=401)

    access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)
