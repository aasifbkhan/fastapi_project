"""
FastAPI dependency providers for repositories and services.
"""
from fastapi import Depends

from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.email_service import EmailService


def get_user_repository() -> UserRepository:
    """Provide a UserRepository instance."""
    return UserRepository()


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    """Provide an AuthService instance."""
    return AuthService(user_repository)


def get_email_service() -> EmailService:
    """Provide an EmailService instance."""
    return EmailService()
