"""
Integration tests for AuthService.
"""
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from models import User
from repositories.user_repository import UserRepository
from schemas.auth import SignupRequest
from services.auth_service import AuthService

@pytest_asyncio.fixture(autouse=True)
async def setup(session):
    """
    Set up the database for integration tests.
    """
    await session.execute(delete(User))
    await session.commit()

class TestAuthService:
    """
    Integration tests for AuthService.
    """

    @pytest.mark.asyncio
    async def test_signup_create_user(self, session):
        """
        Test successful signup creates a user in the database.
        """
        repository = UserRepository()
        auth_service = AuthService(repository)

        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )

        result = await auth_service.signup(data, session)

        assert result is not None
        assert result.id is not None
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.email == "john@example.com"
        assert result.password != "Password123!"

    @pytest.mark.asyncio
    async def test_signup_user_with_duplicate_email(self, session):
        """
        Test signup fails when email already exists.
        """
        repository = UserRepository()
        auth_service = AuthService(repository)

        existing_user = User(
            first_name="Existing",
            last_name="User",
            email="john@example.com",
            password="existing-hashed-password"
        )

        session.add(existing_user)
        await session.commit()

        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )

        with pytest.raises(
            ValueError,
            match="Email already registered"
        ):
            await auth_service.signup(data, session)

        result = await session.execute(
            select(User).where(User.email == "john@example.com")
        )

        users = result.scalars().all()

        assert len(users) == 1
