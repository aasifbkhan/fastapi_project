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
    async with async_session_factory() as session:
        yield session