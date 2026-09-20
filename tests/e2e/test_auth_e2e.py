"""
End-to-end tests for authentication.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

from api.v1.auth.router import SIGNUP_SUCCESS_MESSAGE
from core.database import async_session_factory
from models import AuthTokenType
from repositories.auth_token_repository import AuthTokenRepository
from repositories.user_repository import UserRepository
from services.auth_service import AuthService


async def _issue_verification_token_for_email(email: str) -> str:
    """
    Create a fresh verification token for an existing signup user.

    Used by e2e because only the token hash is stored in the database.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository()
        token_repo = AuthTokenRepository()
        user = await user_repo.get_by_email(email, session)
        assert user is not None
        service = AuthService(user_repo, token_repo)
        return await service._issue_opaque_token(  # pylint: disable=protected-access
            user.id,
            AuthTokenType.EMAIL_VERIFICATION,
            24,
            session,
        )


async def _issue_reset_token_for_email(email: str) -> str:
    async with async_session_factory() as session:
        service = AuthService(UserRepository(), AuthTokenRepository())
        raw = await service.forget_password(email, session)
        assert raw is not None
        return raw


class TestAuthe2e:
    @pytest.mark.asyncio
    async def test_user_can_signup(self):
        email = f"e2e-{uuid4()}@example.com"
        payload = {
            "first_name": "E2E",
            "last_name": "User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        async with AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post("/api/v1/auth/signup", json=payload)
        assert response.status_code == 201
        assert response.json() == {"message": SIGNUP_SUCCESS_MESSAGE}

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self):
        email = f"e2e-{uuid4()}@example.com"
        payload = {
            "first_name": "E2E",
            "last_name": "User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        async with AsyncClient(base_url="http://localhost:8000") as client:
            first_response = await client.post("/api/v1/auth/signup", json=payload)
            second_response = await client.post("/api/v1/auth/signup", json=payload)
        assert first_response.status_code == 201
        assert second_response.status_code == 409

    @pytest.mark.asyncio
    async def test_signup_verify_login_returns_token_pair(self):
        email = f"e2e-{uuid4()}@example.com"
        password = "Password123!"
        payload = {
            "first_name": "E2E",
            "last_name": "User",
            "email": email,
            "password": password,
            "confirm_password": password,
        }
        async with AsyncClient(base_url="http://localhost:8000") as client:
            signup = await client.post("/api/v1/auth/signup", json=payload)
            assert signup.status_code == 201

            inactive_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert inactive_login.status_code == 403

            verify_token = await _issue_verification_token_for_email(email)
            verify = await client.post(
                "/api/v1/auth/verify-email",
                json={"token": verify_token},
            )
            assert verify.status_code == 200

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200
            body = login.json()
            assert body["access_token"]
            assert body["refresh_token"]
            assert body["token_type"] == "bearer"

            refresh = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": body["refresh_token"]},
            )
            assert refresh.status_code == 200
            assert refresh.json()["refresh_token"] != body["refresh_token"]

            reused = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": body["refresh_token"]},
            )
            assert reused.status_code == 401

    @pytest.mark.asyncio
    async def test_forget_reset_login_flow(self):
        email = f"e2e-{uuid4()}@example.com"
        password = "Password123!"
        new_password = "NewPassword123!"
        payload = {
            "first_name": "E2E",
            "last_name": "User",
            "email": email,
            "password": password,
            "confirm_password": password,
        }
        async with AsyncClient(base_url="http://localhost:8000") as client:
            signup = await client.post("/api/v1/auth/signup", json=payload)
            assert signup.status_code == 201
            verify_token = await _issue_verification_token_for_email(email)
            await client.post(
                "/api/v1/auth/verify-email",
                json={"token": verify_token},
            )

            forget = await client.post(
                "/api/v1/auth/forget-password",
                json={"email": email},
            )
            assert forget.status_code == 200

            reset_token = await _issue_reset_token_for_email(email)
            reset = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": reset_token,
                    "password": new_password,
                    "confirm_password": new_password,
                },
            )
            assert reset.status_code == 200

            old_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            new_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": new_password},
            )
            assert old_login.status_code == 401
            assert new_login.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_flow(self):
        email = f"e2e-{uuid4()}@example.com"
        password = "Password123!"
        new_password = "NewPassword123!"
        payload = {
            "first_name": "E2E",
            "last_name": "User",
            "email": email,
            "password": password,
            "confirm_password": password,
        }
        async with AsyncClient(base_url="http://localhost:8000") as client:
            signup = await client.post("/api/v1/auth/signup", json=payload)
            assert signup.status_code == 201
            verify_token = await _issue_verification_token_for_email(email)
            await client.post(
                "/api/v1/auth/verify-email",
                json={"token": verify_token},
            )
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            access = login.json()["access_token"]
            refresh = login.json()["refresh_token"]

            unauth = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": password,
                    "new_password": new_password,
                    "confirm_password": new_password,
                },
            )
            assert unauth.status_code == 401

            change = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {access}"},
                json={
                    "current_password": password,
                    "new_password": new_password,
                    "confirm_password": new_password,
                },
            )
            assert change.status_code == 200

            refresh_after = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh},
            )
            assert refresh_after.status_code == 401

            old_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            new_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": new_password},
            )
            assert old_login.status_code == 401
            assert new_login.status_code == 200
