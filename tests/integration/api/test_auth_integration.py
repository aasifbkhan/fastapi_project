"""
Integration tests for authentication APIs.
"""
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from api.deps import get_email_service
from api.v1.auth.router import SIGNUP_SUCCESS_MESSAGE
from main import app
from models import User


@pytest_asyncio.fixture(autouse=True)
async def setup(session):
    """
    Set up the database for integration tests.
    """
    await session.execute(delete(User))
    await session.commit()


@pytest.fixture(autouse=True)
def disable_rate_limit():
    """
    Disable SlowAPI rate limiting for integration tests.
    """
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True


class TestAuthApi:
    """
    Integration test for auth api.
    """

    @pytest.mark.asyncio
    async def test_signup_api_success(self, session):
        """
        Test successful user signup through the API.
        """
        email_mock = MagicMock()
        app.dependency_overrides[get_email_service] = lambda: email_mock

        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "api/v1/auth/signup",
                    json=payload
                )
        finally:
            app.dependency_overrides.pop(get_email_service, None)

        email_mock.send_email.assert_called_once()
        assert response.status_code == 201
        assert response.json() == {
            "message": SIGNUP_SUCCESS_MESSAGE
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

    @pytest.mark.asyncio
    async def test_signup_api_returns_429_when_rate_limited(self):
        """
        Test signup returns 429 when the rate limit is exceeded.
        """
        app.state.limiter.enabled = True
        app.state.limiter.reset()

        email_mock = MagicMock()
        app.dependency_overrides[get_email_service] = lambda: email_mock

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                responses = []
                for index in range(6):
                    payload = {
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": f"rate-{index}@example.com",
                        "password": "Password123!",
                        "confirm_password": "Password123!",
                    }
                    responses.append(
                        await client.post(
                            "api/v1/auth/signup",
                            json=payload,
                        )
                    )
        finally:
            app.dependency_overrides.pop(get_email_service, None)
            app.state.limiter.enabled = False

        assert responses[5].status_code == 429
