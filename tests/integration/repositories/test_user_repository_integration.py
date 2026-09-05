"""
Integration test of UserRepository
"""
import pytest
import pytest_asyncio
from sqlalchemy import delete
from models import User
from repositories.user_repository import UserRepository

@pytest_asyncio.fixture(autouse=True)
async def setup(session):
    """
    SetUp the database and test fixtures
    """
    await session.execute(delete(User))
    await session.commit()

class TestUserRepository:
    """
    Test UserRepository Functions
    """
    @pytest.mark.asyncio
    async def test_get_by_email_returns_user(self, session):
        """
        Test get_by_email should return user
        """
        repository = UserRepository()
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed-password",
        )

        session.add(user)
        await session.commit()

        result = await repository.get_by_email("john@example.com", session)

        assert result is not None
        assert result.email == "john@example.com"
        assert result.first_name == "John"

    @pytest.mark.asyncio
    async def test_get_by_email_returns_none_when_user_not_exists(self, session):
        """
        Test get_by_email should return none when user not exists
        """
        repository = UserRepository()

        result = await repository.get_by_email(
            "doesnotexist@example.com",
            session
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_user(self, session):
        """
        Test create user
        """
        repository = UserRepository()
        user = User(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="hashed-password",
        )

        result = await repository.create(user, session)

        assert result is user
        assert result.id is not None

        saved_user = await repository.get_by_email(
            "alice@example.com",
            session,
        )
        assert saved_user is not None
        assert saved_user.id == result.id
        assert saved_user.first_name == "Alice"
        assert saved_user.last_name == "Smith"
        assert saved_user.email == "alice@example.com"
