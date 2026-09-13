"""
Authentication related apis (API v1).
"""
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_auth_service, get_email_service
from core.database import get_session
from core.exceptions import EmailAlreadyRegisteredError
from core.rate_limit import limiter
from schemas.auth import SignupRequest, SignupResponse
from services.auth_service import AuthService
from services.email_service import EmailService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

SIGNUP_SUCCESS_MESSAGE = "Sign up successful. Please check your email."


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def user_signup(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    request: Request,  # pylint: disable=unused-argument
    data: SignupRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
    email_service: EmailService = Depends(get_email_service),
):
    """
    User signup request.
    """
    try:
        user = await auth_service.signup(data, session)
        background_tasks.add_task(
            email_service.send_email,
            to=user.email,
            subject="Welcome to DevFlow",
            body=f"Welcome {user.first_name} {user.last_name}!",
        )
        return {"message": SIGNUP_SUCCESS_MESSAGE}
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
