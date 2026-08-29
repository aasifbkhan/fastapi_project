"""
This module handles the user database query related tasks.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
class UserRepository:
    """
    This is UserRepository class which handles the user related databse CRUD operations.
    """

    async def get_by_email(self, email: str, session: AsyncSession) -> User | None:
        """
        This function checks if email is already present.
        """
        result = await session.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    async def create(self, user: User, session: AsyncSession) -> User:
        """
        This function creates new record of user
        """
        session.add(user)

        await session.commit()
        await session.refresh(user)

        return user
