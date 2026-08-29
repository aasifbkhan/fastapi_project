from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

class UserRepository:
    async def get_by_email(self, email: str, session: AsyncSession) -> User | None:
        result = await session.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    async def create(self, user: User, session: AsyncSession) -> User:
        session.add(user)

        await session.commit()
        await session.refresh(user)

        return user