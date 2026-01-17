"""
Async Database Pool - Pool de conexões totalmente assíncrono.

Usa asyncpg (PostgreSQL) ou aiosqlite (SQLite).
Suporta também SQLAlchemy async sessions.
"""

import asyncio
from typing import AsyncGenerator, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from loguru import logger

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


class AsyncDatabasePool:
    """
    Pool de conexões totalmente assíncrono.
    Suporta PostgreSQL (asyncpg) e SQLite (aiosqlite).
    """
    
    def __init__(self, db_url: Optional[str] = None, min_size: int = 5, max_size: int = 20):
        """
        Cria um pool de conexões de banco de dados.
        
        Args:
            db_url: URL do banco de dados. Se None, usa settings.zowpy_db_url
            min_size: Tamanho mínimo do pool
            max_size: Tamanho máximo do pool
        """
        if db_url is None:
            from ..config.settings import settings
            db_url = settings.zowpy_db_url
        
        self.db_url = db_url
        self.min_size = min_size
        self.max_size = max_size
        
        # Determina tipo de DB
        if db_url.startswith("postgresql") or db_url.startswith("postgres"):
            if not HAS_ASYNCPG:
                raise ImportError("asyncpg required for PostgreSQL")
            self._pool: Optional[asyncpg.Pool] = None
            self._db_type = "postgresql"
        elif db_url.startswith("sqlite"):
            if not HAS_AIOSQLITE:
                logger.warning("aiosqlite não disponível, SQLite desabilitado. Instale com: pip install aiosqlite")
                # Permite inicialização sem pool para testes
                self._pool = None
                self._db_type = "sqlite"
            else:
                self._pool: Optional[aiosqlite.Connection] = None
                self._db_type = "sqlite"
        else:
            raise ValueError(f"Unsupported database URL: {db_url}")
        
        # SQLAlchemy async engine e sessionmaker (lazy initialization)
        self._async_engine = None
        self._async_sessionmaker = None
    
    async def initialize(self) -> None:
        """Inicializa pool de forma assíncrona"""
        if self._db_type == "postgresql":
            # Remove prefixo para asyncpg
            db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(
                db_url,
                min_size=self.min_size,
                max_size=self.max_size
            )
        elif self._db_type == "sqlite":
            # Para SQLite, cria conexão única (pooling não é necessário)
            db_path = self.db_url.replace("sqlite+aiosqlite:///", "")
            logger.info(f"Caminho do SQLite: {db_path}")
            self._pool = await aiosqlite.connect(db_path)
        
        # Inicializa SQLAlchemy async engine se disponível
        if HAS_SQLALCHEMY:
            await self._init_sqlalchemy()
    
    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager:
        """Adquire conexão de forma assíncrona"""
        if self._db_type == "postgresql":
            async with self._pool.acquire() as conn:
                yield conn
        elif self._db_type == "sqlite":
            yield self._pool
    
    async def _init_sqlalchemy(self) -> None:
        """Inicializa SQLAlchemy async engine e sessionmaker"""
        if not HAS_SQLALCHEMY:
            return
        
        # Converte URL para formato SQLAlchemy async
        if self._db_type == "postgresql":
            # PostgreSQL: postgresql+asyncpg://
            if self.db_url.startswith("postgresql://"):
                async_url = self.db_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                async_url = self.db_url

        elif self._db_type == "sqlite":
            # SQLite: sqlite+aiosqlite://
            logger.info(f"URL do SQLite: {self.db_url}")

            if self.db_url.startswith("sqlite://"):
                async_url = self.db_url.replace("sqlite://", "sqlite+aiosqlite://")
            else:
                async_url = self.db_url

                
        else:
            return

        logger.info(f"URL do SQLAlchemy: {async_url}")
        
        try:
            self._async_engine = create_async_engine(
                async_url,
                echo=False,
                pool_pre_ping=True,
            )
            self._async_sessionmaker = async_sessionmaker(
                self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        except Exception as e:
            logger.warning(f"Falha ao inicializar SQLAlchemy async engine: {e}")
            self._async_engine = None
            self._async_sessionmaker = None
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Obtém sessão SQLAlchemy async.
        
        Usa SQLAlchemy 2.0 async sessions para operações ORM.
        """
        if not HAS_SQLALCHEMY:
            raise ImportError("SQLAlchemy async support required. Install with: pip install sqlalchemy[asyncio]")
        
        if self._async_sessionmaker is None:
            await self._init_sqlalchemy()
        
        if self._async_sessionmaker is None:
            raise RuntimeError("SQLAlchemy async sessionmaker not initialized")
        
        async with self._async_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def close(self) -> None:
        """Fecha pool de forma assíncrona"""
        if self._db_type == "postgresql":
            await self._pool.close()
        elif self._db_type == "sqlite":
            await self._pool.close()
        
        # Fecha SQLAlchemy engine
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_sessionmaker = None





