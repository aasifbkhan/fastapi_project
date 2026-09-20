"""
Database access for auth_tokens (verification, reset, refresh).
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import AuthToken


class AuthTokenRepository:
    """CRUD helpers for AuthToken rows."""

    async def create(self, token: AuthToken, session: AsyncSession) -> AuthToken:
        """Insert a new auth token row."""
        session.add(token)
        await session.commit()
        await session.refresh(token)
        return token

    async def get_valid_by_hash_and_type(
        self,
        token_hash: str,
        token_type: str,
        session: AsyncSession,
    ) -> AuthToken | None:
        """
        Return an unused, unexpired token matching hash and type, or None.
        """
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == token_hash,
                AuthToken.token_type == token_type,
                AuthToken.used_at.is_(None),  # pylint: disable=no-member
                AuthToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_hash_and_type(
        self,
        token_hash: str,
        token_type: str,
        session: AsyncSession,
    ) -> AuthToken | None:
        """Return a token by hash and type regardless of used/expiry state."""
        result = await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == token_hash,
                AuthToken.token_type == token_type,
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_user_tokens(
        self,
        user_id: UUID,
        token_type: str,
        session: AsyncSession,
        *,
        commit: bool = True,
    ) -> None:
        """Mark all unused tokens of a type for a user as used (invalidated)."""
        now = datetime.now(timezone.utc)
        await session.execute(
            update(AuthToken)
            .where(
                AuthToken.user_id == user_id,
                AuthToken.token_type == token_type,
                AuthToken.used_at.is_(None),  # pylint: disable=no-member
            )
            .values(used_at=now)
        )
        if commit:
            await session.commit()

    async def mark_used(
        self,
        token: AuthToken,
        session: AsyncSession,
        *,
        commit: bool = True,
    ) -> AuthToken:
        """Mark a single token as used."""
        token.used_at = datetime.now(timezone.utc)
        session.add(token)
        if commit:
            await session.commit()
            await session.refresh(token)
        return token
