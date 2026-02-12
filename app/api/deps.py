"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MCCError
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db
from app.services.openrouter import OpenRouterClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except InvalidTokenError as e:
        raise MCCError(
            code="INVALID_TOKEN", message="Invalid or expired token", status_code=401
        ) from e

    if payload.get("type") != "access":
        raise MCCError(code="INVALID_TOKEN", message="Not an access token", status_code=401)

    user_id = payload.get("sub")
    if user_id is None:
        raise MCCError(code="INVALID_TOKEN", message="Token missing subject", status_code=401)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise MCCError(code="USER_NOT_FOUND", message="User not found", status_code=401)

    if not user.is_active:
        raise MCCError(code="USER_INACTIVE", message="User account is inactive", status_code=403)

    return user


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise MCCError(code="FORBIDDEN", message="Admin access required", status_code=403)
    return user


def get_openrouter(request: Request) -> OpenRouterClient:
    return request.app.state.openrouter
