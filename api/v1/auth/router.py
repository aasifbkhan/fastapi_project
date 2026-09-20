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

from api.deps import get_auth_service, get_current_user, get_email_service
from core.config import settings
from core.database import get_session
from core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    WrongPasswordError,
)
from core.rate_limit import limiter
from models import User
from schemas.auth import (
    ChangePasswordRequest,
    ForgetPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
)
from services.auth_service import AuthService
from services.email_service import EmailService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

SIGNUP_SUCCESS_MESSAGE = "Sign up successful. Please check your email."
VERIFY_EMAIL_SUCCESS_MESSAGE = "Email verified successfully."
FORGET_PASSWORD_SUCCESS_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)
RESET_PASSWORD_SUCCESS_MESSAGE = "Password has been reset successfully."
CHANGE_PASSWORD_SUCCESS_MESSAGE = "Password changed successfully."


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
        user, raw_token = await auth_service.signup(data, session)
        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
        background_tasks.add_task(
            email_service.send_email,
            to=user.email,
            subject="Verify your DevFlow email",
            body=(
                f"Hi {user.first_name},\n\n"
                f"Please verify your email by opening this link:\n{verify_link}\n"
            ),
        )
        return {"message": SIGNUP_SUCCESS_MESSAGE}
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,  # pylint: disable=unused-argument
    data: VerifyEmailRequest,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Verify email using the token from the signup email."""
    try:
        await auth_service.verify_email(data.token, session)
        return {"message": VERIFY_EMAIL_SUCCESS_MESSAGE}
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def login(
    request: Request,  # pylint: disable=unused-argument
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate and return access + refresh tokens."""
    try:
        return await auth_service.login(data, session)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def refresh_tokens(
    request: Request,  # pylint: disable=unused-argument
    data: RefreshRequest,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Exchange a refresh token for a new access + refresh pair."""
    try:
        return await auth_service.refresh(data.refresh_token, session)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post(
    "/forget-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("3/minute")
async def forget_password(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    request: Request,  # pylint: disable=unused-argument
    data: ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
    email_service: EmailService = Depends(get_email_service),
):
    """Request a password reset email (always returns a generic success message)."""
    raw_token = await auth_service.forget_password(data.email, session)
    if raw_token:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        background_tasks.add_task(
            email_service.send_email,
            to=data.email,
            subject="Reset your DevFlow password",
            body=(
                "You requested a password reset.\n\n"
                f"Open this link to reset your password:\n{reset_link}\n"
            ),
        )
    return {"message": FORGET_PASSWORD_SUCCESS_MESSAGE}


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,  # pylint: disable=unused-argument
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Reset password using a token from the forget-password email."""
    try:
        await auth_service.reset_password(data.token, data.password, session)
        return {"message": RESET_PASSWORD_SUCCESS_MESSAGE}
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def change_password(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    request: Request,  # pylint: disable=unused-argument
    data: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
):
    """Change password for the authenticated user."""
    try:
        await auth_service.change_password(
            current_user,
            data.current_password,
            data.new_password,
            session,
        )
        return {"message": CHANGE_PASSWORD_SUCCESS_MESSAGE}
    except WrongPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
