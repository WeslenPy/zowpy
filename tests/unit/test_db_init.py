"""
Testes unitários para db/init.py
"""

import pytest
import os
import tempfile
from zowpy.db import init_db, init_db_from_url, AsyncDatabasePool, Base


@pytest.mark.asyncio
async def test_init_db_from_url_sqlite():
    """Testa inicialização de banco SQLite a partir de URL"""
    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_url = f"sqlite+aiosqlite:///{db_path}"
        await init_db_from_url(db_url)
        
        # Verifica que o arquivo foi criado
        assert os.path.exists(db_path)
        
        # Verifica que as tabelas foram criadas
        db_pool = AsyncDatabasePool(db_url)
        await db_pool.initialize()
        
        try:
            async with db_pool.acquire() as conn:
                async with conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """) as cursor:
                    tables = await cursor.fetchall()
                    table_names = [row[0] for row in tables]
            
            # Verifica tabelas principais do schema unificado
            assert "accounts" in table_names
            assert "identities" in table_names
            assert "sessions" in table_names
            assert "prekeys" in table_names
            assert "signed_prekeys" in table_names
            assert "profile_configs" in table_names
            assert "client_configs" in table_names
            assert "contacts" in table_names
            assert "groups" in table_names
        
        finally:
            await db_pool.close()
    
    finally:
        # Limpa arquivo temporário
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_init_db_from_pool():
    """Testa inicialização de banco a partir de pool"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_url = f"sqlite+aiosqlite:///{db_path}"
        db_pool = AsyncDatabasePool(db_url)
        await db_pool.initialize()
        
        try:
            await init_db(db_pool=db_pool)
            
            # Verifica que o arquivo foi criado
            assert os.path.exists(db_path)
            
            # Verifica que as tabelas foram criadas
            async with db_pool.acquire() as conn:
                async with conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """) as cursor:
                    tables = await cursor.fetchall()
                    assert len(tables) >= 15  # Pelo menos 15 tabelas
        
        finally:
            await db_pool.close()
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_init_db_drop_existing():
    """Testa inicialização com drop_existing=True"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_url = f"sqlite+aiosqlite:///{db_path}"
        
        # Cria banco inicial
        await init_db_from_url(db_url)
        
        db_pool = AsyncDatabasePool(db_url)
        await db_pool.initialize()
        
        try:
            # Verifica que tabelas foram criadas
            async with db_pool.acquire() as conn:
                async with conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name = 'accounts'
                """) as cursor:
                    result = await cursor.fetchone()
                    assert result is not None  # Tabela deve existir
            
            # Reinicializa com drop_existing
            await init_db_from_url(db_url, drop_existing=True)
            
            # Verifica que tabelas do Base foram recriadas
            async with db_pool.acquire() as conn:
                async with conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name = 'accounts'
                """) as cursor:
                    result = await cursor.fetchone()
                    assert result is not None  # Tabela deve existir após recriação
            
            # Verifica que todas as tabelas esperadas existem
            async with db_pool.acquire() as conn:
                async with conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """) as cursor:
                    tables = await cursor.fetchall()
                    table_names = [row[0] for row in tables]
            
            # Verifica que tabelas principais existem
            assert "accounts" in table_names
            assert "identities" in table_names
            assert "sessions" in table_names
        
        finally:
            await db_pool.close()
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_init_db_checkfirst():
    """Testa que init_db não falha se tabelas já existem (checkfirst=True)"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_url = f"sqlite+aiosqlite:///{db_path}"
        
        # Cria banco inicial
        await init_db_from_url(db_url)
        
        # Tenta criar novamente (não deve falhar)
        await init_db_from_url(db_url)
        
        # Verifica que ainda funciona
        assert os.path.exists(db_path)
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_all_tables_created():
    """Testa que todas as tabelas esperadas foram criadas"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db_url = f"sqlite+aiosqlite:///{db_path}"
        await init_db_from_url(db_url)
        
        db_pool = AsyncDatabasePool(db_url)
        await db_pool.initialize()
        
        try:
            async with db_pool.acquire() as conn:
                async with conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """) as cursor:
                    tables = await cursor.fetchall()
                    table_names = [row[0] for row in tables]
            
            # Lista de tabelas esperadas
            expected_tables = [
                "accounts",
                "identities",
                "prekeys",
                "sessions",
                "signed_prekeys",
                "account_state",
                "contacts",
                "group_participants",
                "groups",
                "profile_configs",
                "client_configs",
                "sent_messages",
            ]
            
            # Verifica que todas as tabelas esperadas existem
            for table in expected_tables:
                assert table in table_names, f"Tabela {table} não foi criada"
        
        finally:
            await db_pool.close()
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

