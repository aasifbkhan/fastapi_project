"""
Unit tests for password hashing, JWT helpers, and token hashing.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from core.config import settings
from core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_url_safe_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_hash_password():
    """
    Test password is getting hashed
    """
    password = "Password123!"
    hashed_password = hash_password(password)

    assert hashed_password != password
    assert hashed_password


def test_verify_password_success():
    """
    Test password verification is success
    """
    password = "Password123!"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True


def test_verify_password_failure():
    """
    Test password verification is failed
    """
    password = "Password123!"
    hashed_password = hash_password(password)

    assert verify_password("WrongPassword123!", hashed_password) is False


def test_generate_url_safe_token_is_non_empty():
    token = generate_url_safe_token()
    assert isinstance(token, str)
    assert len(token) > 20


def test_hash_token_is_deterministic():
    raw = "opaque-token-value"
    assert hash_token(raw) == hash_token(raw)
    assert hash_token(raw) != raw
    assert len(hash_token(raw)) == 64


def test_create_and_decode_access_token():
    token = create_access_token("user-id-123")
    payload = decode_token(token, TOKEN_TYPE_ACCESS)
    assert payload["sub"] == "user-id-123"
    assert payload["type"] == TOKEN_TYPE_ACCESS


def test_create_and_decode_refresh_token():
    token = create_refresh_token("user-id-123")
    payload = decode_token(token, TOKEN_TYPE_REFRESH)
    assert payload["sub"] == "user-id-123"
    assert payload["type"] == TOKEN_TYPE_REFRESH


def test_decode_token_rejects_wrong_type():
    token = create_access_token("user-id-123")
    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(token, TOKEN_TYPE_REFRESH)


def test_decode_token_rejects_invalid_token():
    with pytest.raises(jwt.PyJWTError):
        decode_token("not-a-valid-jwt", TOKEN_TYPE_ACCESS)


def test_decode_token_rejects_expired_token():
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": "user-id-123", "type": TOKEN_TYPE_ACCESS, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, TOKEN_TYPE_ACCESS)
