from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from schemas.auth import SignupRequest, SignupResponse
from repositories.user_repository import UserRepository
from services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

user_repository = UserRepository()
auth_service = AuthService(user_repository)

@router.post("/signup", response_model=SignupResponse,status_code=status.HTTP_201_CREATED)
async def user_signup(data: SignupRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await auth_service.signup(data, session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)
        )