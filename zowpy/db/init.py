"""
Database Initialization - Criação de banco de dados e tabelas.

Função assíncrona para criar todas as tabelas do banco de dados.
"""

import asyncio
from typing import Optional
from loguru import logger

from .pool import AsyncDatabasePool
from .models import Base
from .models import *


async def init_db(
    db_pool: Optional[AsyncDatabasePool] = None,
    db_url: Optional[str] = None,
    drop_existing: bool = False
) -> None:
    """
    Inicializa banco de dados criando todas as tabelas.
    
    Args:
        db_pool: Pool de banco de dados (opcional, se fornecido usa ele)
        db_url: URL do banco de dados (opcional, se fornecido cria pool temporário)
        drop_existing: Se True, dropa tabelas existentes antes de criar (perigoso!)
    
    Raises:
        ValueError: Se nem db_pool nem db_url forem fornecidos
    """
    # Usa settings como padrão se nenhum parâmetro for fornecido
    if db_pool is None and db_url is None:
        from ..config.settings import settings
        db_url = settings.zowpy_db_url
    
    # Cria pool temporário se necessário
    temp_pool = None
    if db_pool is None:
        db_pool = AsyncDatabasePool(db_url)
        await db_pool.initialize()
        temp_pool = db_pool
    
    try:
        logger.info(f"Inicializando banco de dados: {db_pool.db_url}")
        
        # Gera SQL CREATE TABLE para todas as tabelas
        if db_pool._db_type == "postgresql":
            await _init_postgresql(db_pool, drop_existing)
        elif db_pool._db_type == "sqlite":
            await _init_sqlite(db_pool, drop_existing)
        else:
            raise ValueError(f"Unsupported database type: {db_pool._db_type}")
        
        logger.info("Banco de dados inicializado com sucesso")

    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
    
    finally:
        # Fecha pool temporário se foi criado
        if temp_pool:
            await temp_pool.close()


async def _init_postgresql(db_pool: AsyncDatabasePool, drop_existing: bool) -> None:
    """Inicializa banco PostgreSQL"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.schema import CreateTable
    
    # Cria engine síncrono para metadata
    # Remove prefixo asyncpg para engine síncrono
    sync_url = db_pool.db_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url, echo=True)
    
    try:
        if drop_existing:
            logger.warning("Dropping existing tables...")
            # Dropa todas as tabelas usando metadata
            Base.metadata.drop_all(engine, checkfirst=True)
            logger.info("Tabelas existentes removidas")
        
        # Cria todas as tabelas usando metadata
        Base.metadata.create_all(engine)
        logger.info("Tabelas criadas no PostgreSQL")
    
    finally:
        engine.dispose()


async def _init_sqlite(db_pool: AsyncDatabasePool, drop_existing: bool) -> None:
    """Inicializa banco SQLite"""
    from sqlalchemy import create_engine
    
    # Extrai path do SQLite
    db_path = db_pool.db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

    logger.info(f"Caminho do SQLite: {db_path}")
    
    # Cria engine síncrono para metadata
    sync_url = f"sqlite:///{db_path}"
    engine = create_engine(sync_url, echo=True)
    
    try:
        if drop_existing:
            logger.warning("Dropping existing tables...")
            # Dropa todas as tabelas usando metadata
            Base.metadata.drop_all(engine, checkfirst=True)
            logger.info("Tabelas existentes removidas")
        
        # Cria todas as tabelas usando metadata
        Base.metadata.create_all(engine)
        logger.info("Tabelas criadas no SQLite")

    except Exception as e:
        logger.error(f"Erro ao inicializar SQLite: {e}")
        raise
    
    finally:
        engine.dispose()


async def init_db_from_url(db_url: str, drop_existing: bool = False) -> None:
    """
    Inicializa banco de dados a partir de URL.
    
    Conveniência para criar pool temporário e inicializar.
    
    Args:
        db_url: URL do banco de dados
        drop_existing: Se True, dropa tabelas existentes antes de criar
    """
    await init_db(db_url=db_url, drop_existing=drop_existing)


async def drop_all_tables(db_pool: AsyncDatabasePool) -> None:
    """
    Dropa todas as tabelas do banco de dados.
    
    ⚠️ PERIGOSO: Remove todos os dados!
    
    Args:
        db_pool: Pool de banco de dados
    """
    logger.warning("⚠️ Dropping all tables - THIS WILL DELETE ALL DATA!")
    
    if db_pool._db_type == "postgresql":
        sync_url = db_pool.db_url.replace("postgresql+asyncpg://", "postgresql://")
        from sqlalchemy import create_engine
        engine = create_engine(sync_url, echo=False)
        try:
            Base.metadata.drop_all(engine, checkfirst=True)
            logger.info("All tables dropped from PostgreSQL")
        finally:
            engine.dispose()
    
    elif db_pool._db_type == "sqlite":
        db_path = db_pool.db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        sync_url = f"sqlite:///{db_path}"
        from sqlalchemy import create_engine
        engine = create_engine(sync_url, echo=False)
        try:
            Base.metadata.drop_all(engine, checkfirst=True)
            logger.info("All tables dropped from SQLite")
        finally:
            engine.dispose()
