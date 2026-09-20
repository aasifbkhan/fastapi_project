"""
FastAPI dependency providers for repositories and services.
"""
from fastapi import Depends, HTTPException, Request, status

from models import User
from repositories.auth_token_repository import AuthTokenRepository
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.email_service import EmailService


def get_user_repository() -> UserRepository:
    """Provide a UserRepository instance."""
    return UserRepository()


def get_auth_token_repository() -> AuthTokenRepository:
    """Provide an AuthTokenRepository instance."""
    return AuthTokenRepository()


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    auth_token_repository: AuthTokenRepository = Depends(get_auth_token_repository),
) -> AuthService:
    """Provide an AuthService instance."""
    return AuthService(user_repository, auth_token_repository)


def get_email_service() -> EmailService:
    """Provide an EmailService instance."""
    return EmailService()


def get_current_user(request: Request) -> User:
    """
    Return the user attached by AuthJWTMiddleware.

    Defense in depth for protected handlers; middleware performs JWT validation.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
