from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool, QueuePool

from core.config import settings
from core.database import engine, async_session_factory


def test_engine_created():
    assert engine is not None
    assert engine.echo is settings.SQL_ECHO


def test_engine_pool_configuration():
    if settings.DATABASE_NULL_POOL:
        assert isinstance(engine.pool, NullPool)
    else:
        assert isinstance(engine.pool, QueuePool)


def test_session_factory_configuration():
    assert async_session_factory.class_ is AsyncSession
    assert async_session_factory.kw["expire_on_commit"] is False
