"""Security utilities — stubs for PR #2, implemented in PR #4."""


def hash_password(password: str) -> str:
    raise NotImplementedError


def verify_password(plain: str, hashed: str) -> bool:
    raise NotImplementedError


def create_access_token(data: dict) -> str:
    raise NotImplementedError


def create_refresh_token(data: dict) -> str:
    raise NotImplementedError


def decode_token(token: str) -> dict:
    raise NotImplementedError
