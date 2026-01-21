from typing import Any, AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


from sqlalchemy.orm.session import sessionmaker

from zowpy.config.settings import Settings

from contextlib import asynccontextmanager
from loguru import logger



settings = Settings()

logger.info("Criando engine assincrona!")

conf_engine = dict(
    url=settings.zowpy_db_url,
    echo=settings.zowpy_db_echo,
)

if  settings.zowpy_db_url.lower().strip().startswith(("mysql", "postgresql")):
    extend = dict(
        pool_pre_ping=True,
        pool_size=settings.zowpy_db_pool_size,
        max_overflow=settings.zowpy_db_max_overflow,
        pool_recycle=settings.zowpy_db_pool_recycle,
        pool_timeout=settings.zowpy_db_pool_timeout,
    )
    conf_engine.update(extend)
    
else:
    conf_engine.update(dict(connect_args={"check_same_thread": False}))


engine: AsyncEngine = create_async_engine(**conf_engine)


AsyncSessionMaker =  async_sessionmaker(bind=engine,
                                             expire_on_commit=False)


def create_sync_session():
    return sessionmaker(bind=engine,expire_on_commit=False)


async def get_async_session(session=None) ->  AsyncGenerator[AsyncSession, None]:
        
    async with AsyncSessionMaker() as new_session:
        logger.info(f"Criando nova sessão sessão: {new_session}")
        yield new_session
        
        
@asynccontextmanager
async def get_async_session_with_context(session=None) ->  AsyncGenerator[AsyncSession, None]:
        
    async with AsyncSessionMaker() as new_session:
        logger.info(f"Criando nova sessão sessão: {new_session}")
        yield new_session
        await new_session.commit()
        await new_session.close()
        
