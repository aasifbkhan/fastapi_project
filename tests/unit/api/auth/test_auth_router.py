"""
Unit tests for authentication router.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.auth.router import SIGNUP_SUCCESS_MESSAGE, user_signup
from core.exceptions import EmailAlreadyRegisteredError
from core.rate_limit import limiter
from models import User
from schemas.auth import SignupRequest


def _make_request() -> Request:
    """Build a minimal Starlette Request for SlowAPI."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/auth/signup",
        "raw_path": b"/api/v1/auth/signup",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def disable_rate_limit():
    """Disable SlowAPI rate limiting for router unit tests."""
    previous = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = previous


class TestAuthRouter:
    """
    Unit tests for authentication router.
    """
    @pytest.mark.asyncio
    async def test_signup_success(self):
        """
        Test successful user signup.
        """
        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!"
        )

        request = _make_request()
        session = MagicMock()
        background_tasks = MagicMock()
        auth_service = MagicMock()
        email_service = MagicMock()

        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed-password",
        )

        auth_service.signup = AsyncMock(return_value=user)

        result = await user_signup(
            request=request,
            data=data,
            background_tasks=background_tasks,
            session=session,
            auth_service=auth_service,
            email_service=email_service,
        )

        assert result == {"message": SIGNUP_SUCCESS_MESSAGE}

        auth_service.signup.assert_awaited_once_with(data, session)

        background_tasks.add_task.assert_called_once_with(
            email_service.send_email,
            to=data.email,
            subject="Welcome to DevFlow",
            body="Welcome John Doe!",
        )

    @pytest.mark.asyncio
    async def test_signup_returns_conflict_when_user_exists(self):
        """
        Test signup returns 409 when email is already registered.
        """
        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )

        request = _make_request()
        session = MagicMock()
        background_tasks = MagicMock()
        auth_service = MagicMock()
        email_service = MagicMock()

        auth_service.signup = AsyncMock(
            side_effect=EmailAlreadyRegisteredError()
        )

        with pytest.raises(HTTPException) as exc_info:
            await user_signup(
                request=request,
                data=data,
                background_tasks=background_tasks,
                session=session,
                auth_service=auth_service,
                email_service=email_service,
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Email already registered"

        auth_service.signup.assert_awaited_once_with(data, session)

    @pytest.mark.asyncio
    async def test_signup_does_not_schedule_email_when_signup_fails(self):
        """
        Test no email is scheduled when signup fails.
        """
        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )

        request = _make_request()
        session = MagicMock()
        background_tasks = MagicMock()
        auth_service = MagicMock()
        email_service = MagicMock()

        auth_service.signup = AsyncMock(
            side_effect=EmailAlreadyRegisteredError()
        )

        with pytest.raises(HTTPException):
            await user_signup(
                request=request,
                data=data,
                background_tasks=background_tasks,
                session=session,
                auth_service=auth_service,
                email_service=email_service,
            )

        background_tasks.add_task.assert_not_called()
