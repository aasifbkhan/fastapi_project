"""
Database configuration and session creation.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=True
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_= AsyncSession,
    expire_on_commit=False
)

async def get_session():
    """
    Database session created to execute sql queries
    """
    async with async_session_factory() as session:
        yield session
