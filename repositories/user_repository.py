"""
This module handles the user database query related tasks.
"""
from uuid import UUID

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

    async def get_by_id(self, user_id: UUID, session: AsyncSession) -> User | None:
        """Load a user by primary key."""
        result = await session.execute(
            select(User).where(User.id == user_id)
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

    async def update(self, user: User, session: AsyncSession) -> User:
        """Persist updates to an existing user."""
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
