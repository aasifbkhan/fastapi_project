from sqlalchemy.ext.asyncio import AsyncSession
from core.database import engine, async_session_factory

def test_engine_created():
    assert engine is not None
    assert engine.echo is True

def test_session_factory_configuration():
    assert async_session_factory.class_ is AsyncSession
    assert async_session_factory.kw["expire_on_commit"] is False