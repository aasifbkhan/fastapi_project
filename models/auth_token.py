"""
Auth token model for email verification, password reset, and refresh tokens.
"""
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel
from uuid6 import uuid7


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class AuthTokenType(str, Enum):
    """Supported auth token kinds stored in auth_tokens."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    REFRESH = "refresh"


class AuthToken(SQLModel, table=True):
    """Persisted hashed tokens for verification, reset, and refresh flows."""

    __tablename__ = "auth_tokens"

    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        nullable=False,
    )
    user_id: UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=False,
    )
    token_hash: str = Field(
        max_length=255,
        unique=True,
        index=True,
        nullable=False,
    )
    token_type: str = Field(
        max_length=50,
        index=True,
        nullable=False,
    )
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
