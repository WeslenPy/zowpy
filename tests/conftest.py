

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from zowpy.db.config.base import Model

TEST_DATABASE_URL = 'sqlite+aiosqlite:///:memory:'

import pytest
import pytest_asyncio

@pytest.fixture(scope='session')
def test_engine():
    """Create test database engine."""
    # Import models to register them
    from zowpy.db.models import (
        Account,
        Identity,
        PreKey,
        SignedPreKey,
        SessionKey,
        SenderKey,
        Poll,
        AppStateKey,
        Contact,
        Broadcast,
        TrustedContact,
        TaskMsg,
    )

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        echo=False,
    )

    yield engine


@pytest_asyncio.fixture
async def db_session(test_engine:AsyncEngine):
    """Create a database session for each test."""
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        
        #SQLite3
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.commit()

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        
    async with test_engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)

    await test_engine.dispose()
