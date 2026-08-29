from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repository import UserRepository
from schemas.auth import SignupRequest
from core.security import hash_password
from models.user import User

class AuthService:
    def __init__(
        self,
        user_repository: UserRepository
    ):
        self.user_repository = user_repository

    async def signup(self, data: SignupRequest, session: AsyncSession):
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

        try:
            await self.user_repository.create(user, session)
            return {"message": "User registerd succesfully"}
        except Exception as exc:
            raise
        
        