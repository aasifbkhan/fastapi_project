"""
Integration tests for authentication APIs.
"""
from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from main import app
from models import User

@pytest_asyncio.fixture(autouse=True)
async def setup(session):
    """
    Set up the database for integration tests.
    """
    await session.execute(delete(User))
    await session.commit()

class TestAuthApi:
    """
    Integration test for auth api.
    """

    @pytest.mark.asyncio
    async def test_signup_api_success(self, session, monkeypatch):
        """
        Test successful user signup through the API.
        """

        email_mock = AsyncMock()
        monkeypatch.setattr(
            "api.auth.router.email_service.send_email",
            email_mock,
        )

        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "api/v1/auth/signup",
                json=payload
            )

        email_mock.assert_awaited_once()
        assert response.status_code == 201
        assert response.json() == {
            "message": "Sign up successfull..!! Please check your email to verify the email."
        }

        result = await session.execute(
            select(User).where(User.email == "john@example.com")
        )

        user = result.scalar_one_or_none()

        assert user is not None
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email == "john@example.com"
        assert user.password != "Password123!"

    @pytest.mark.asyncio
    async def test_signup_api_returns_409_when_email_exists(self, session):
        """
        Test signup returns 409 when email already exists.
        """
        existing_user = User(
            first_name="Existing",
            last_name="User",
            email="john@example.com",
            password="existing-hashed-password",
        )

        session.add(existing_user)
        await session.commit()

        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "api/v1/auth/signup",
                json=payload
            )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Email already registered"
        }

    @pytest.mark.asyncio
    async def test_signup_api_returns_422_when_confrim_password_missing(self):
        """
        Test signup returns 422 when confirm_password is missing.
        """
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "api/v1/auth/signup",
                json=payload
            )

        assert response.status_code == 422
