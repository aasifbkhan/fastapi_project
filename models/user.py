"""
This module has the user table model
"""
from datetime import datetime, timezone
from uuid import UUID
from sqlmodel import SQLModel, Field
from uuid6 import uuid7
from sqlalchemy import DateTime

class User(SQLModel, table=True):
    """
    This class represents the user table
    """
    __tablename__ = "users"
    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        nullable=False
    )
    first_name: str = Field(
        max_length=255,
        index=True,
        nullable=False
    )
    last_name: str = Field(
        max_length=255,
        index=True,
        nullable=False
    )
    email: str = Field(
        max_length=255,
        unique=True,
        index=True,
        nullable=False
    )
    password: str = Field(
        max_length=255,
        nullable=False
    )
    is_active: bool = Field(
        default=False,
        nullable=False
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
