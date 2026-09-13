"""
Unit tests for API dependency providers.
"""
from api.deps import get_auth_service, get_email_service, get_user_repository
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.email_service import EmailService


def test_get_user_repository_returns_repository():
    assert isinstance(get_user_repository(), UserRepository)


def test_get_auth_service_returns_service():
    repository = UserRepository()
    service = get_auth_service(user_repository=repository)
    assert isinstance(service, AuthService)
    assert service.user_repository is repository


def test_get_email_service_returns_service():
    assert isinstance(get_email_service(), EmailService)
