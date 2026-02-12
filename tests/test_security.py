"""Tests for password hashing, JWT tokens, and TOTP verification."""

import pyotp
import pytest
from jwt import InvalidTokenError

from app.core.security import (
    create_2fa_temp_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp,
)


def test_hash_and_verify_password():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_hash_produces_different_hashes():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # argon2 salts should differ


def test_create_and_decode_access_token():
    token = create_access_token({"sub": "user-123"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "jti" in payload


def test_create_and_decode_refresh_token():
    token = create_refresh_token({"sub": "user-456"})
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_create_and_decode_2fa_temp_token():
    token = create_2fa_temp_token({"sub": "user-789"})
    payload = decode_token(token)
    assert payload["sub"] == "user-789"
    assert payload["type"] == "2fa_temp"


def test_expired_token_rejected():
    from datetime import timedelta

    token = create_access_token({"sub": "user-exp"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(InvalidTokenError):
        decode_token(token)


def test_token_type_distinguishable():
    access = create_access_token({"sub": "u1"})
    refresh = create_refresh_token({"sub": "u1"})
    temp = create_2fa_temp_token({"sub": "u1"})

    assert decode_token(access)["type"] == "access"
    assert decode_token(refresh)["type"] == "refresh"
    assert decode_token(temp)["type"] == "2fa_temp"


def test_verify_totp():
    secret = generate_totp_secret()
    totp = pyotp.TOTP(secret)
    code = totp.now()
    assert verify_totp(secret, code)
    assert not verify_totp(secret, "000000")


def test_totp_secret_generation():
    s1 = generate_totp_secret()
    s2 = generate_totp_secret()
    assert s1 != s2
    assert len(s1) > 10
