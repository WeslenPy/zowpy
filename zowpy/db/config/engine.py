from typing import Any, AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

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

if settings.zowpy_db_url.lower().strip().startswith(("mysql", "postgresql")):
    conf_engine.update(
        dict(
            pool_pre_ping=True,
            pool_size=settings.zowpy_db_pool_size,
            max_overflow=settings.zowpy_db_max_overflow,
            pool_recycle=settings.zowpy_db_pool_recycle,
            pool_timeout=settings.zowpy_db_pool_timeout,
        )
    )
else:
    # SQLite: StaticPool evita "no active connection" com muitas contas/async.
    # Uma única conexão persistente, reutilizada por todas as sessões (acesso serializado ao DB).
    # timeout: segundos que o SQLite espera pelo lock do arquivo (default 5); 60 reduz "database is locked".
    conf_engine.update(
        dict(
            # poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                # "timeout": 60,
            },
        )
    )


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
        
