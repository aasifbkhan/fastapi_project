"""
Security module creates and verify hash password and JWT tokens.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from core.config import settings

password_hasher = PasswordHasher()

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(password: str) -> str:
    """
    This function creates hash password
    """
    return password_hasher.hash(password)


def verify_password(password, hashed_password) -> bool:
    """
    This function verfiy the hash password
    """
    try:
        password_hasher.verify(hashed_password, password)
        return True
    except VerifyMismatchError:
        return False


def generate_url_safe_token() -> str:
    """Generate a URL-safe opaque token for email verification / password reset."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """Return a SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_access_token(subject: str) -> str:
    """Create a short-lived access JWT."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "type": TOKEN_TYPE_ACCESS,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    """Create a longer-lived refresh JWT."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject,
        "type": TOKEN_TYPE_REFRESH,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str, expected_type: str) -> dict:
    """
    Decode and validate a JWT, ensuring the type claim matches expected_type.

    Raises jwt.PyJWTError subclasses on invalid/expired tokens, or ValueError
    when the type claim does not match.
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    return payload
