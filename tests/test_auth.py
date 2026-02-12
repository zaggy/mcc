"""Tests for authentication endpoints."""

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import generate_totp_secret, hash_password
from app.db.models import User
from app.db.session import Base, get_db
from app.main import app

_base = settings.DATABASE_URL.rsplit("/", 1)[0]
TEST_DB_URL = f"{_base}/mcc_test"


@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db: AsyncSession):
    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    user = User(
        username="testuser",
        email="test@test.com",
        password_hash=hash_password("testpass123"),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    return user


@pytest.fixture
async def test_user_2fa(db: AsyncSession) -> tuple[User, str]:
    secret = generate_totp_secret()
    user = User(
        username="user2fa",
        email="2fa@test.com",
        password_hash=hash_password("testpass123"),
        is_active=True,
        is_2fa_enabled=True,
        totp_secret=secret,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    return user, secret


async def test_login_success(client: AsyncClient, test_user: User):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, test_user: User):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "nobody",
            "password": "whatever",
        },
    )
    assert resp.status_code == 401


async def test_login_2fa_returns_temp_token(client: AsyncClient, test_user_2fa: tuple[User, str]):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "user2fa",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["requires_2fa"] is True
    assert "temp_token" in data


async def test_2fa_verify_success(client: AsyncClient, test_user_2fa: tuple[User, str]):
    user, secret = test_user_2fa

    # Login to get temp token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "user2fa",
            "password": "testpass123",
        },
    )
    temp_token = login_resp.json()["temp_token"]

    # Verify with TOTP code
    totp = pyotp.TOTP(secret)
    resp = await client.post(
        "/api/v1/auth/2fa/verify",
        json={
            "temp_token": temp_token,
            "code": totp.now(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_2fa_verify_wrong_code(client: AsyncClient, test_user_2fa: tuple[User, str]):
    # Login to get temp token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "user2fa",
            "password": "testpass123",
        },
    )
    temp_token = login_resp.json()["temp_token"]

    resp = await client.post(
        "/api/v1/auth/2fa/verify",
        json={
            "temp_token": temp_token,
            "code": "000000",
        },
    )
    assert resp.status_code == 401


async def test_refresh_token(client: AsyncClient, test_user: User):
    # Login first
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpass123",
        },
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Refresh
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_refresh_with_access_token_rejected(client: AsyncClient, test_user: User):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpass123",
        },
    )
    access_token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": access_token,
        },
    )
    assert resp.status_code == 401


async def test_inactive_user_login_rejected(client: AsyncClient, db: AsyncSession):
    user = User(
        username="inactive",
        email="inactive@test.com",
        password_hash=hash_password("testpass123"),
        is_active=False,
    )
    db.add(user)
    await db.flush()
    await db.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "inactive",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 403
