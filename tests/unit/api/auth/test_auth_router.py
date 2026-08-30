"""
Unit tests for authentication router.
"""
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
import pytest

from api.auth.router import user_signup
from schemas.auth import SignupRequest
from models import User

class TestAuthRouter:
    """
    Unit tests for authentication router.
    """
    @pytest.mark.asyncio
    async def test_signup_success(self, monkeypatch):
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

        session = MagicMock()
        background_tasks = MagicMock()

        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed-password",
        )

        signup_mock = AsyncMock(return_value=user)

        monkeypatch.setattr(
            "api.auth.router.auth_service.signup",
            signup_mock,
        )

        email_mock = AsyncMock()
        
        monkeypatch.setattr(
            "api.auth.router.email_service.send_email",
            email_mock,
        )

        result = await user_signup(
            data=data,
            background_tasks=background_tasks,
            session=session,
        )

        assert result == {
            "message": (
                "Sign up successfull..!! "
                "Please check your email to verify the email."
            )
        }

        signup_mock.assert_awaited_once_with(data, session)

        background_tasks.add_task.assert_called_once_with(
            email_mock,
            to="khanaasifb98@gmail.com",
            subject="Test Email",
            body="Welcome John Doe!",
        )

    @pytest.mark.asyncio
    async def test_signup_returns_conflict_when_user_exists(
        self,
        monkeypatch,
    ):
        """
        Test signup returns 409 when signup service raises ValueError.
        """
        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )

        session = MagicMock()
        background_tasks = MagicMock()

        signup_mock = AsyncMock(
            side_effect=ValueError("Email already registered")
        )

        monkeypatch.setattr(
            "api.auth.router.auth_service.signup",
            signup_mock,
        )

        with pytest.raises(Exception) as exc_info:
            await user_signup(
                data=data,
                background_tasks=background_tasks,
                session=session,
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Email already registered"

        signup_mock.assert_awaited_once_with(data, session)

    @pytest.mark.asyncio
    async def test_signup_does_not_schedule_email_when_signup_fails(
        self,
        monkeypatch,
    ):
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

        session = MagicMock()
        background_tasks = MagicMock()

        signup_mock = AsyncMock(
            side_effect=ValueError("Email already registered")
        )

        monkeypatch.setattr(
            "api.auth.router.auth_service.signup",
            signup_mock,
        )

        with pytest.raises(Exception):
            await user_signup(
                data=data,
                background_tasks=background_tasks,
                session=session,
            )

        background_tasks.add_task.assert_not_called()