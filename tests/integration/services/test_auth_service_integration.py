"""
Integration tests for AuthService.
"""
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
)
from core.security import hash_token, verify_password
from models import AuthToken, AuthTokenType, User
from repositories.auth_token_repository import AuthTokenRepository
from repositories.user_repository import UserRepository
from schemas.auth import LoginRequest, SignupRequest
from services.auth_service import AuthService


@pytest_asyncio.fixture(autouse=True)
async def setup(session):
    await session.execute(delete(AuthToken))
    await session.execute(delete(User))
    await session.commit()


def _service() -> AuthService:
    return AuthService(UserRepository(), AuthTokenRepository())


class TestAuthService:
    @pytest.mark.asyncio
    async def test_signup_create_user(self, session):
        auth_service = _service()
        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )

        user, raw_token = await auth_service.signup(data, session)

        assert user.id is not None
        assert user.is_active is False
        assert raw_token
        result = await session.execute(
            select(AuthToken).where(
                AuthToken.user_id == user.id,
                AuthToken.token_type == AuthTokenType.EMAIL_VERIFICATION.value,
            )
        )
        token = result.scalar_one()
        assert token.token_hash == hash_token(raw_token)

    @pytest.mark.asyncio
    async def test_signup_user_with_duplicate_email(self, session):
        auth_service = _service()
        session.add(
            User(
                first_name="Existing",
                last_name="User",
                email="john@example.com",
                password="existing-hashed-password",
            )
        )
        await session.commit()

        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )

        with pytest.raises(EmailAlreadyRegisteredError):
            await auth_service.signup(data, session)

        result = await session.execute(
            select(User).where(User.email == "john@example.com")
        )
        assert len(result.scalars().all()) == 1

    @pytest.mark.asyncio
    async def test_verify_email_activates_user(self, session):
        auth_service = _service()
        user, raw_token = await auth_service.signup(
            SignupRequest(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password="Password123!",
                confirm_password="Password123!",
            ),
            session,
        )

        verified = await auth_service.verify_email(raw_token, session)
        assert verified.is_active is True

    @pytest.mark.asyncio
    async def test_login_returns_token_pair(self, session):
        auth_service = _service()
        user, raw_token = await auth_service.signup(
            SignupRequest(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password="Password123!",
                confirm_password="Password123!",
            ),
            session,
        )
        await auth_service.verify_email(raw_token, session)

        tokens = await auth_service.login(
            LoginRequest(email="john@example.com", password="Password123!"),
            session,
        )
        assert tokens["access_token"]
        assert tokens["refresh_token"]
        assert tokens["token_type"] == "bearer"

        result = await session.execute(
            select(AuthToken).where(
                AuthToken.user_id == user.id,
                AuthToken.token_type == AuthTokenType.REFRESH.value,
            )
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_login_rejects_inactive(self, session):
        auth_service = _service()
        await auth_service.signup(
            SignupRequest(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password="Password123!",
                confirm_password="Password123!",
            ),
            session,
        )
        with pytest.raises(InactiveUserError):
            await auth_service.login(
                LoginRequest(email="john@example.com", password="Password123!"),
                session,
            )

    @pytest.mark.asyncio
    async def test_refresh_rotates_tokens(self, session):
        auth_service = _service()
        _user, raw_token = await auth_service.signup(
            SignupRequest(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password="Password123!",
                confirm_password="Password123!",
            ),
            session,
        )
        await auth_service.verify_email(raw_token, session)
        first = await auth_service.login(
            LoginRequest(email="john@example.com", password="Password123!"),
            session,
        )
        second = await auth_service.refresh(first["refresh_token"], session)
        assert second["access_token"]
        assert second["refresh_token"] != first["refresh_token"]

        with pytest.raises(Exception):
            await auth_service.refresh(first["refresh_token"], session)

    @pytest.mark.asyncio
    async def test_reset_password_updates_hash(self, session):
        auth_service = _service()
        user, verify_token = await auth_service.signup(
            SignupRequest(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password="Password123!",
                confirm_password="Password123!",
            ),
            session,
        )
        await auth_service.verify_email(verify_token, session)
        reset_token = await auth_service.forget_password("john@example.com", session)
        await auth_service.reset_password(reset_token, "NewPassword123!", session)

        result = await session.execute(select(User).where(User.id == user.id))
        updated = result.scalar_one()
        assert verify_password("NewPassword123!", updated.password)
        assert not verify_password("Password123!", updated.password)

        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                LoginRequest(email="john@example.com", password="Password123!"),
                session,
            )
