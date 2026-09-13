"""
Unit tests for authentication router (API v1).
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.v1.auth.router import (
    CHANGE_PASSWORD_SUCCESS_MESSAGE,
    FORGET_PASSWORD_SUCCESS_MESSAGE,
    RESET_PASSWORD_SUCCESS_MESSAGE,
    SIGNUP_SUCCESS_MESSAGE,
    VERIFY_EMAIL_SUCCESS_MESSAGE,
    change_password,
    forget_password,
    login,
    refresh_tokens,
    reset_password,
    user_signup,
    verify_email,
)
from core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    WrongPasswordError,
)
from core.rate_limit import limiter
from models import User
from schemas.auth import (
    ChangePasswordRequest,
    ForgetPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyEmailRequest,
)


def _make_request(path: str = "/api/v1/auth/signup") -> Request:
    """Build a minimal Starlette Request for SlowAPI."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
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
    """Unit tests for authentication router."""

    @pytest.mark.asyncio
    async def test_signup_success(self):
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
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed-password",
        )
        auth_service.signup = AsyncMock(return_value=(user, "verify-token"))

        with patch("api.v1.auth.router.settings") as mock_settings:
            mock_settings.FRONTEND_URL = "http://localhost:3000"
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
        background_tasks.add_task.assert_called_once()
        call_kwargs = background_tasks.add_task.call_args.kwargs
        assert call_kwargs["to"] == data.email
        assert call_kwargs["subject"] == "Verify your DevFlow email"
        assert "verify-token" in call_kwargs["body"]

    @pytest.mark.asyncio
    async def test_signup_returns_conflict_when_user_exists(self):
        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )
        auth_service = MagicMock()
        auth_service.signup = AsyncMock(side_effect=EmailAlreadyRegisteredError())

        with pytest.raises(HTTPException) as exc_info:
            await user_signup(
                request=_make_request(),
                data=data,
                background_tasks=MagicMock(),
                session=MagicMock(),
                auth_service=auth_service,
                email_service=MagicMock(),
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_signup_does_not_schedule_email_when_signup_fails(self):
        data = SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )
        background_tasks = MagicMock()
        auth_service = MagicMock()
        auth_service.signup = AsyncMock(side_effect=EmailAlreadyRegisteredError())

        with pytest.raises(HTTPException):
            await user_signup(
                request=_make_request(),
                data=data,
                background_tasks=background_tasks,
                session=MagicMock(),
                auth_service=auth_service,
                email_service=MagicMock(),
            )

        background_tasks.add_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_email_success(self):
        auth_service = MagicMock()
        auth_service.verify_email = AsyncMock()
        result = await verify_email(
            request=_make_request("/api/v1/auth/verify-email"),
            data=VerifyEmailRequest(token="tok"),
            session=MagicMock(),
            auth_service=auth_service,
        )
        assert result == {"message": VERIFY_EMAIL_SUCCESS_MESSAGE}

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self):
        auth_service = MagicMock()
        auth_service.verify_email = AsyncMock(side_effect=InvalidTokenError())
        with pytest.raises(HTTPException) as exc_info:
            await verify_email(
                request=_make_request("/api/v1/auth/verify-email"),
                data=VerifyEmailRequest(token="bad"),
                session=MagicMock(),
                auth_service=auth_service,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(self):
        auth_service = MagicMock()
        auth_service.login = AsyncMock(
            return_value={
                "access_token": "a",
                "refresh_token": "r",
                "token_type": "bearer",
            }
        )
        result = await login(
            request=_make_request("/api/v1/auth/login"),
            data=LoginRequest(email="john@example.com", password="Password123!"),
            session=MagicMock(),
            auth_service=auth_service,
        )
        assert result["access_token"] == "a"
        assert result["refresh_token"] == "r"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        auth_service = MagicMock()
        auth_service.login = AsyncMock(side_effect=InvalidCredentialsError())
        with pytest.raises(HTTPException) as exc_info:
            await login(
                request=_make_request("/api/v1/auth/login"),
                data=LoginRequest(email="john@example.com", password="bad"),
                session=MagicMock(),
                auth_service=auth_service,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self):
        auth_service = MagicMock()
        auth_service.login = AsyncMock(side_effect=InactiveUserError())
        with pytest.raises(HTTPException) as exc_info:
            await login(
                request=_make_request("/api/v1/auth/login"),
                data=LoginRequest(email="john@example.com", password="Password123!"),
                session=MagicMock(),
                auth_service=auth_service,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_refresh_success(self):
        auth_service = MagicMock()
        auth_service.refresh = AsyncMock(
            return_value={
                "access_token": "a2",
                "refresh_token": "r2",
                "token_type": "bearer",
            }
        )
        result = await refresh_tokens(
            request=_make_request("/api/v1/auth/refresh"),
            data=RefreshRequest(refresh_token="r"),
            session=MagicMock(),
            auth_service=auth_service,
        )
        assert result["access_token"] == "a2"

    @pytest.mark.asyncio
    async def test_forget_password_schedules_email_when_token_issued(self):
        auth_service = MagicMock()
        auth_service.forget_password = AsyncMock(return_value="reset-token")
        background_tasks = MagicMock()
        email_service = MagicMock()

        with patch("api.v1.auth.router.settings") as mock_settings:
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            result = await forget_password(
                request=_make_request("/api/v1/auth/forget-password"),
                data=ForgetPasswordRequest(email="john@example.com"),
                background_tasks=background_tasks,
                session=MagicMock(),
                auth_service=auth_service,
                email_service=email_service,
            )

        assert result == {"message": FORGET_PASSWORD_SUCCESS_MESSAGE}
        background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_forget_password_no_email_when_user_missing(self):
        auth_service = MagicMock()
        auth_service.forget_password = AsyncMock(return_value=None)
        background_tasks = MagicMock()

        result = await forget_password(
            request=_make_request("/api/v1/auth/forget-password"),
            data=ForgetPasswordRequest(email="missing@example.com"),
            background_tasks=background_tasks,
            session=MagicMock(),
            auth_service=auth_service,
            email_service=MagicMock(),
        )

        assert result == {"message": FORGET_PASSWORD_SUCCESS_MESSAGE}
        background_tasks.add_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        auth_service = MagicMock()
        auth_service.reset_password = AsyncMock()
        result = await reset_password(
            request=_make_request("/api/v1/auth/reset-password"),
            data=ResetPasswordRequest(
                token="tok",
                password="NewPassword123!",
                confirm_password="NewPassword123!",
            ),
            session=MagicMock(),
            auth_service=auth_service,
        )
        assert result == {"message": RESET_PASSWORD_SUCCESS_MESSAGE}

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        auth_service = MagicMock()
        auth_service.change_password = AsyncMock()
        user = User(
            id=uuid4(),
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed",
            is_active=True,
        )
        result = await change_password(
            request=_make_request("/api/v1/auth/change-password"),
            data=ChangePasswordRequest(
                current_password="Password123!",
                new_password="NewPassword123!",
                confirm_password="NewPassword123!",
            ),
            session=MagicMock(),
            auth_service=auth_service,
            current_user=user,
        )
        assert result == {"message": CHANGE_PASSWORD_SUCCESS_MESSAGE}

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self):
        auth_service = MagicMock()
        auth_service.change_password = AsyncMock(side_effect=WrongPasswordError())
        user = User(
            id=uuid4(),
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="hashed",
            is_active=True,
        )
        with pytest.raises(HTTPException) as exc_info:
            await change_password(
                request=_make_request("/api/v1/auth/change-password"),
                data=ChangePasswordRequest(
                    current_password="WrongPassword123!",
                    new_password="NewPassword123!",
                    confirm_password="NewPassword123!",
                ),
                session=MagicMock(),
                auth_service=auth_service,
                current_user=user,
            )
        assert exc_info.value.status_code == 400
