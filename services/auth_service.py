"""
This module contains authentication related classes and fuctions.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repository import UserRepository
from schemas.auth import SignupRequest
from core.security import hash_password
from models import User

class AuthService:
    """
    This class provide functions to sighnup, login, logout, 
    change password, forget password, email verifacation.
    """
    def __init__(
        self,
        user_repository: UserRepository,
    ):
        self.user_repository = user_repository

    async def signup(self, data: SignupRequest, session: AsyncSession):
        """
        This function signup the new user in the application
        """
        existing_email = await self.user_repository.get_by_email(
            data.email,
            session
        )

        if existing_email:
            raise ValueError("Email already registered")

        hashed_password = hash_password(data.password)

        user = User(
            first_name = data.first_name,
            last_name = data.last_name,
            email = data.email,
            password = hashed_password
        )

        return await self.user_repository.create(user, session)
