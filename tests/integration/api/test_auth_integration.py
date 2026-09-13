"""
Integration tests for authentication APIs.
"""
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from api.deps import get_email_service
from api.v1.auth.router import (
    CHANGE_PASSWORD_SUCCESS_MESSAGE,
    FORGET_PASSWORD_SUCCESS_MESSAGE,
    RESET_PASSWORD_SUCCESS_MESSAGE,
    SIGNUP_SUCCESS_MESSAGE,
    VERIFY_EMAIL_SUCCESS_MESSAGE,
)
from main import app
from models import AuthToken, User
from repositories.auth_token_repository import AuthTokenRepository
from repositories.user_repository import UserRepository
from schemas.auth import SignupRequest
from services.auth_service import AuthService


@pytest_asyncio.fixture(autouse=True)
async def setup(session):
    await session.execute(delete(AuthToken))
    await session.execute(delete(User))
    await session.commit()


@pytest.fixture(autouse=True)
def disable_rate_limit():
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True


def _auth_service() -> AuthService:
    return AuthService(UserRepository(), AuthTokenRepository())


async def _signup_and_verify(session, email: str = "john@example.com"):
    service = _auth_service()
    user, raw_token = await service.signup(
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email=email,
            password="Password123!",
            confirm_password="Password123!",
        ),
        session,
    )
    await service.verify_email(raw_token, session)
    return user


class TestAuthApi:
    @pytest.mark.asyncio
    async def test_signup_api_success(self, session):
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
                base_url="http://test",
            ) as client:
                response = await client.post("api/v1/auth/signup", json=payload)
        finally:
            app.dependency_overrides.pop(get_email_service, None)

        email_mock.send_email.assert_called_once()
        assert response.status_code == 201
        assert response.json() == {"message": SIGNUP_SUCCESS_MESSAGE}

        result = await session.execute(
            select(User).where(User.email == "john@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.password != "Password123!"
        assert user.is_active is False

        tokens = await session.execute(
            select(AuthToken).where(AuthToken.user_id == user.id)
        )
        assert tokens.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_signup_api_returns_409_when_email_exists(self, session):
        session.add(
            User(
                first_name="Existing",
                last_name="User",
                email="john@example.com",
                password="existing-hashed-password",
            )
        )
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
            base_url="http://test",
        ) as client:
            response = await client.post("api/v1/auth/signup", json=payload)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_signup_api_returns_422_when_confrim_password_missing(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
        }
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("api/v1/auth/signup", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_api_returns_429_when_rate_limited(self):
        app.state.limiter.enabled = True
        app.state.limiter.reset()
        email_mock = MagicMock()
        app.dependency_overrides[get_email_service] = lambda: email_mock
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
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
                        await client.post("api/v1/auth/signup", json=payload)
                    )
        finally:
            app.dependency_overrides.pop(get_email_service, None)
            app.state.limiter.enabled = False
        assert responses[5].status_code == 429

    @pytest.mark.asyncio
    async def test_verify_email_api_activates_user(self, session):
        service = _auth_service()
        user, raw_token = await service.signup(
            SignupRequest(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password="Password123!",
                confirm_password="Password123!",
            ),
            session,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "api/v1/auth/verify-email",
                json={"token": raw_token},
            )
        assert response.status_code == 200
        assert response.json() == {"message": VERIFY_EMAIL_SUCCESS_MESSAGE}
        await session.refresh(user)
        result = await session.execute(select(User).where(User.id == user.id))
        assert result.scalar_one().is_active is True

    @pytest.mark.asyncio
    async def test_login_api_returns_tokens(self, session):
        await _signup_and_verify(session)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "Password123!"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_api_rejects_inactive(self, session):
        service = _auth_service()
        await service.signup(
            SignupRequest(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password="Password123!",
                confirm_password="Password123!",
            ),
            session,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "Password123!"},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_login_api_rejects_bad_credentials(self, session):
        await _signup_and_verify(session)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "WrongPassword123!"},
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_api_rotates_tokens(self, session):
        await _signup_and_verify(session)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            login_response = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "Password123!"},
            )
            refresh_token = login_response.json()["refresh_token"]
            refresh_response = await client.post(
                "api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            reused = await client.post(
                "api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
        assert refresh_response.status_code == 200
        assert refresh_response.json()["refresh_token"] != refresh_token
        assert reused.status_code == 401

    @pytest.mark.asyncio
    async def test_forget_password_always_200(self, session):
        email_mock = MagicMock()
        app.dependency_overrides[get_email_service] = lambda: email_mock
        await _signup_and_verify(session)
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                known = await client.post(
                    "api/v1/auth/forget-password",
                    json={"email": "john@example.com"},
                )
                unknown = await client.post(
                    "api/v1/auth/forget-password",
                    json={"email": "missing@example.com"},
                )
        finally:
            app.dependency_overrides.pop(get_email_service, None)

        assert known.status_code == 200
        assert unknown.status_code == 200
        assert known.json() == {"message": FORGET_PASSWORD_SUCCESS_MESSAGE}
        assert unknown.json() == {"message": FORGET_PASSWORD_SUCCESS_MESSAGE}
        email_mock.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_api(self, session):
        await _signup_and_verify(session)
        service = _auth_service()
        raw_token = await service.forget_password("john@example.com", session)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "api/v1/auth/reset-password",
                json={
                    "token": raw_token,
                    "password": "NewPassword123!",
                    "confirm_password": "NewPassword123!",
                },
            )
            login_old = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "Password123!"},
            )
            login_new = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "NewPassword123!"},
            )
        assert response.status_code == 200
        assert response.json() == {"message": RESET_PASSWORD_SUCCESS_MESSAGE}
        assert login_old.status_code == 401
        assert login_new.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_api(self, session):
        await _signup_and_verify(session)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            login_response = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "Password123!"},
            )
            access = login_response.json()["access_token"]
            refresh = login_response.json()["refresh_token"]
            change = await client.post(
                "api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {access}"},
                json={
                    "current_password": "Password123!",
                    "new_password": "NewPassword123!",
                    "confirm_password": "NewPassword123!",
                },
            )
            wrong_auth = await client.post(
                "api/v1/auth/change-password",
                json={
                    "current_password": "Password123!",
                    "new_password": "NewPassword123!",
                    "confirm_password": "NewPassword123!",
                },
            )
            refresh_after = await client.post(
                "api/v1/auth/refresh",
                json={"refresh_token": refresh},
            )
            login_new = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "NewPassword123!"},
            )
        assert change.status_code == 200
        assert change.json() == {"message": CHANGE_PASSWORD_SUCCESS_MESSAGE}
        assert wrong_auth.status_code == 401
        assert refresh_after.status_code == 401
        assert login_new.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, session):
        await _signup_and_verify(session)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            login_response = await client.post(
                "api/v1/auth/login",
                json={"email": "john@example.com", "password": "Password123!"},
            )
            access = login_response.json()["access_token"]
            response = await client.post(
                "api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {access}"},
                json={
                    "current_password": "WrongPassword123!",
                    "new_password": "NewPassword123!",
                    "confirm_password": "NewPassword123!",
                },
            )
        assert response.status_code == 400
