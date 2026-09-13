"""
This contains all database table models
"""
from .auth_token import AuthToken, AuthTokenType
from .user import User

__all__ = ["User", "AuthToken", "AuthTokenType"]
