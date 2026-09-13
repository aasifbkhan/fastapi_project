"""
Database configuration and session creation.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from core.config import settings

_engine_kwargs = {
    "echo": settings.SQL_ECHO,
}
if settings.DATABASE_NULL_POOL:
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session():
    """
    Database session created to execute sql queries
    """
    async with async_session_factory() as session:
        yield session
