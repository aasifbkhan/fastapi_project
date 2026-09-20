"""
Integration tests for AuthTokenRepository.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete

from core.security import hash_token
from models import AuthToken, AuthTokenType, User
from repositories.auth_token_repository import AuthTokenRepository
from repositories.user_repository import UserRepository


@pytest_asyncio.fixture(autouse=True)
async def setup(session):
    await session.execute(delete(AuthToken))
    await session.execute(delete(User))
    await session.commit()


@pytest.mark.asyncio
async def test_create_and_get_valid_token(session):
    user_repo = UserRepository()
    token_repo = AuthTokenRepository()
    user = await user_repo.create(
        User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed",
        ),
        session,
    )
    raw = "opaque-token"
    token = AuthToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        token_type=AuthTokenType.EMAIL_VERIFICATION.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    created = await token_repo.create(token, session)
    found = await token_repo.get_valid_by_hash_and_type(
        hash_token(raw),
        AuthTokenType.EMAIL_VERIFICATION.value,
        session,
    )
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_mark_used_and_invalidate(session):
    user_repo = UserRepository()
    token_repo = AuthTokenRepository()
    user = await user_repo.create(
        User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed",
        ),
        session,
    )
    token = await token_repo.create(
        AuthToken(
            user_id=user.id,
            token_hash=hash_token("a"),
            token_type=AuthTokenType.REFRESH.value,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        ),
        session,
    )
    await token_repo.mark_used(token, session)
    assert token.used_at is not None

    await token_repo.create(
        AuthToken(
            user_id=user.id,
            token_hash=hash_token("b"),
            token_type=AuthTokenType.REFRESH.value,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        ),
        session,
    )
    await token_repo.invalidate_user_tokens(
        user.id,
        AuthTokenType.REFRESH.value,
        session,
    )
    found = await token_repo.get_valid_by_hash_and_type(
        hash_token("b"),
        AuthTokenType.REFRESH.value,
        session,
    )
    assert found is None
