"""
This module contains authentication related classes and fuctions.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    WrongPasswordError,
)
from core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_url_safe_token,
    hash_password,
    hash_token,
    verify_password,
)
from models import AuthToken, AuthTokenType, User
from repositories.auth_token_repository import AuthTokenRepository
from repositories.user_repository import UserRepository
from schemas.auth import LoginRequest, SignupRequest


class AuthService:
    """
    This class provide functions to sighnup, login, logout,
    change password, forget password, email verifacation.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        auth_token_repository: AuthTokenRepository,
    ):
        self.user_repository = user_repository
        self.auth_token_repository = auth_token_repository

    async def _issue_opaque_token(
        self,
        user_id: UUID,
        token_type: AuthTokenType,
        expire_hours: int,
        session: AsyncSession,
    ) -> str:
        """Invalidate prior tokens of this type and create a new opaque token."""
        await self.auth_token_repository.invalidate_user_tokens(
            user_id,
            token_type.value,
            session,
            commit=False,
        )
        raw_token = generate_url_safe_token()
        token = AuthToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            token_type=token_type.value,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expire_hours),
        )
        await self.auth_token_repository.create(token, session)
        return raw_token

    async def _issue_token_pair(
        self,
        user: User,
        session: AsyncSession,
    ) -> dict[str, str]:
        """Create access + refresh JWTs and persist the refresh hash."""
        subject = str(user.id)
        access_token = create_access_token(subject)
        refresh_token = create_refresh_token(subject)
        refresh_row = AuthToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            token_type=AuthTokenType.REFRESH.value,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        await self.auth_token_repository.create(refresh_row, session)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def _resolve_opaque_token(
        self,
        raw_token: str,
        token_type: AuthTokenType,
        session: AsyncSession,
    ) -> AuthToken:
        """Validate an opaque token; raise InvalidTokenError or TokenExpiredError."""
        token_hash = hash_token(raw_token)
        valid = await self.auth_token_repository.get_valid_by_hash_and_type(
            token_hash,
            token_type.value,
            session,
        )
        if valid is not None:
            return valid

        existing = await self.auth_token_repository.get_by_hash_and_type(
            token_hash,
            token_type.value,
            session,
        )
        if existing is None:
            raise InvalidTokenError()
        if existing.used_at is not None:
            raise InvalidTokenError("Token has already been used")
        raise TokenExpiredError()

    async def signup(self, data: SignupRequest, session: AsyncSession):
        """
        Signup a new user and issue an email verification token.

        Returns (user, raw_verification_token).
        """
        existing_email = await self.user_repository.get_by_email(
            data.email,
            session,
        )

        if existing_email:
            raise EmailAlreadyRegisteredError()

        hashed_password = hash_password(data.password)

        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=hashed_password,
        )

        try:
            user = await self.user_repository.create(user, session)
        except IntegrityError as exc:
            await session.rollback()
            raise EmailAlreadyRegisteredError() from exc

        raw_token = await self._issue_opaque_token(
            user.id,
            AuthTokenType.EMAIL_VERIFICATION,
            settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
            session,
        )
        return user, raw_token

    async def verify_email(self, token: str, session: AsyncSession) -> User:
        """Activate a user using a valid email verification token."""
        auth_token = await self._resolve_opaque_token(
            token,
            AuthTokenType.EMAIL_VERIFICATION,
            session,
        )
        user = await self.user_repository.get_by_id(auth_token.user_id, session)
        if user is None:
            raise InvalidTokenError()

        user.is_active = True
        await self.auth_token_repository.mark_used(auth_token, session, commit=False)
        await self.user_repository.update(user, session)
        return user

    async def login(self, data: LoginRequest, session: AsyncSession) -> dict[str, str]:
        """Authenticate user and return access + refresh tokens."""
        user = await self.user_repository.get_by_email(data.email, session)
        if user is None or not verify_password(data.password, user.password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()
        return await self._issue_token_pair(user, session)

    async def refresh(
        self,
        refresh_token: str,
        session: AsyncSession,
    ) -> dict[str, str]:
        """Rotate a refresh token into a new access + refresh pair."""
        try:
            payload = decode_token(refresh_token, TOKEN_TYPE_REFRESH)
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError() from exc
        except (jwt.PyJWTError, ValueError) as exc:
            raise InvalidTokenError() from exc

        token_hash = hash_token(refresh_token)
        stored = await self.auth_token_repository.get_valid_by_hash_and_type(
            token_hash,
            AuthTokenType.REFRESH.value,
            session,
        )
        if stored is None:
            raise InvalidTokenError()

        user_id = UUID(payload["sub"])
        user = await self.user_repository.get_by_id(user_id, session)
        if user is None or not user.is_active:
            raise InvalidTokenError()

        await self.auth_token_repository.mark_used(stored, session, commit=False)
        return await self._issue_token_pair(user, session)

    async def forget_password(
        self,
        email: str,
        session: AsyncSession,
    ) -> str | None:
        """
        Issue a password reset token if the user exists.

        Returns raw token or None (caller always returns a generic success message).
        """
        user = await self.user_repository.get_by_email(email, session)
        if user is None:
            return None

        return await self._issue_opaque_token(
            user.id,
            AuthTokenType.PASSWORD_RESET,
            settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS,
            session,
        )

    async def reset_password(
        self,
        token: str,
        new_password: str,
        session: AsyncSession,
    ) -> User:
        """Reset password using a valid reset token; invalidate refresh sessions."""
        auth_token = await self._resolve_opaque_token(
            token,
            AuthTokenType.PASSWORD_RESET,
            session,
        )
        user = await self.user_repository.get_by_id(auth_token.user_id, session)
        if user is None:
            raise InvalidTokenError()

        user.password = hash_password(new_password)
        await self.auth_token_repository.mark_used(auth_token, session, commit=False)
        await self.auth_token_repository.invalidate_user_tokens(
            user.id,
            AuthTokenType.PASSWORD_RESET.value,
            session,
            commit=False,
        )
        await self.auth_token_repository.invalidate_user_tokens(
            user.id,
            AuthTokenType.REFRESH.value,
            session,
            commit=False,
        )
        await self.user_repository.update(user, session)
        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        session: AsyncSession,
    ) -> User:
        """Change password for an authenticated user; invalidate refresh sessions."""
        db_user = await self.user_repository.get_by_id(user.id, session)
        if db_user is None:
            raise InvalidCredentialsError()

        if not verify_password(current_password, db_user.password):
            raise WrongPasswordError()

        db_user.password = hash_password(new_password)
        await self.auth_token_repository.invalidate_user_tokens(
            db_user.id,
            AuthTokenType.REFRESH.value,
            session,
            commit=False,
        )
        await self.user_repository.update(db_user, session)
        return db_user
