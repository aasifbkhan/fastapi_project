"""
Unit tests for API dependency providers.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.deps import (
    get_auth_service,
    get_auth_token_repository,
    get_current_user,
    get_email_service,
    get_user_repository,
)
from models import User
from repositories.auth_token_repository import AuthTokenRepository
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.email_service import EmailService


def test_get_user_repository_returns_repository():
    assert isinstance(get_user_repository(), UserRepository)


def test_get_auth_token_repository_returns_repository():
    assert isinstance(get_auth_token_repository(), AuthTokenRepository)


def test_get_auth_service_returns_service():
    user_repository = UserRepository()
    token_repository = AuthTokenRepository()
    service = get_auth_service(
        user_repository=user_repository,
        auth_token_repository=token_repository,
    )
    assert isinstance(service, AuthService)
    assert service.user_repository is user_repository
    assert service.auth_token_repository is token_repository


def test_get_email_service_returns_service():
    assert isinstance(get_email_service(), EmailService)


def test_get_current_user_returns_user_from_request_state():
    user = User(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
    )
    request = MagicMock(spec=Request)
    request.state.user = user
    assert get_current_user(request) is user


def test_get_current_user_raises_when_missing():
    request = MagicMock(spec=Request)
    request.state.user = None
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request)
    assert exc_info.value.status_code == 401
