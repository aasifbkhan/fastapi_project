"""
Unit tests for AuthJWTMiddleware.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from core.security import create_access_token, create_refresh_token
from middleware.auth import AuthJWTMiddleware, PROTECTED_PATHS, PUBLIC_PATHS
from models import User


async def _ok(_request):
    return JSONResponse({"ok": True})


def _build_app():
    app = Starlette(
        routes=[
            Route("/api/v1/auth/login", _ok, methods=["POST"]),
            Route("/api/v1/auth/change-password", _ok, methods=["POST"]),
            Route("/other", _ok, methods=["GET"]),
        ]
    )
    app.add_middleware(AuthJWTMiddleware)
    return app


@pytest.mark.asyncio
async def test_public_path_passes_without_authorization():
    app = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unprotected_path_passes_without_authorization():
    app = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/other")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_path_without_header_returns_401():
    app = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/change-password")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_protected_path_with_invalid_token_returns_401():
    app = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_path_rejects_refresh_token_type():
    app = _build_app()
    refresh = create_refresh_token(str(uuid4()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {refresh}"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_path_with_valid_access_token_allows_request():
    app = _build_app()
    user_id = uuid4()
    user = User(
        id=user_id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
        is_active=True,
    )
    access = create_access_token(str(user_id))

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.expunge = MagicMock()

    with patch("middleware.auth.async_session_factory", return_value=mock_session), patch(
        "middleware.auth.UserRepository"
    ) as repo_cls:
        repo_cls.return_value.get_by_id = AsyncMock(return_value=user)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {access}"},
            )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_path_inactive_user_returns_401():
    app = _build_app()
    user_id = uuid4()
    user = User(
        id=user_id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
        is_active=False,
    )
    access = create_access_token(str(user_id))

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("middleware.auth.async_session_factory", return_value=mock_session), patch(
        "middleware.auth.UserRepository"
    ) as repo_cls:
        repo_cls.return_value.get_by_id = AsyncMock(return_value=user)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {access}"},
            )

    assert response.status_code == 401


def test_public_and_protected_path_sets():
    assert "/api/v1/auth/login" in PUBLIC_PATHS
    assert "/api/v1/auth/change-password" in PROTECTED_PATHS
