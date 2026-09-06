"""
Authentication related apis
"""
from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from schemas.auth import SignupRequest, SignupResponse
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.email_service import EmailService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

user_repository = UserRepository()
auth_service = AuthService(user_repository)
email_service = EmailService()

@router.post("/signup", response_model=SignupResponse,status_code=status.HTTP_201_CREATED)
async def user_signup(
    data: SignupRequest, background_tasks:
    BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    User signup request.
    """
    try:
        user = await auth_service.signup(data, session)
        background_tasks.add_task(
            email_service.send_email,
            to=user.email,
            subject="Test Email",
            body=f"Welcome {user.first_name} {user.last_name}!"
        )
        return {"message": "Sign up successfull..!! Please check your email to verify the email."}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)
        ) from exc
