import pytest_asyncio

from core.database import async_session_factory


@pytest_asyncio.fixture
async def session():
    async with async_session_factory() as session:
        yield session