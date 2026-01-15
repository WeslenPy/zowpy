"""
Testes unitários para core/store.py
"""

import pytest

from zowpy.db.pool import AsyncDatabasePool
from zowpy.db import init_db
from zowpy.core.store import AsyncStateStore


@pytest.mark.asyncio
async def test_store_init():
    """Testa inicialização do store"""
    db_pool = AsyncDatabasePool("sqlite+aiosqlite:///:memory:")
    # não inicializa (teste apenas de wiring)
    store = AsyncStateStore("5511999999999", db_pool)
    
    assert store.account_id == "5511999999999"
    assert store.db_pool == db_pool


@pytest.mark.asyncio
async def test_store_get_set():
    """Testa get e set de valores"""
    # Usa SQLite em arquivo temporário (in-memory não compartilha bem entre engine/conn em alguns cenários)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_pool = AsyncDatabasePool(f"sqlite+aiosqlite:///{db_path}")
    await db_pool.initialize()
    await init_db(db_pool=db_pool)

    store = AsyncStateStore("5511999999999", db_pool)
    
    # Testa set
    await store.set("test_key", "test_value")
    
    # Verifica cache
    assert store._cache.get("test_key") == "test_value"
    
    # Testa get
    value = await store.get("test_key")
    assert value == "test_value"

    await db_pool.close()


@pytest.mark.asyncio
async def test_store_get_not_found():
    """Testa get de chave não encontrada"""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_pool = AsyncDatabasePool(f"sqlite+aiosqlite:///{db_path}")
    await db_pool.initialize()
    await init_db(db_pool=db_pool)

    store = AsyncStateStore("5511999999999", db_pool)
    
    value = await store.get("nonexistent")
    assert value is None

    await db_pool.close()


@pytest.mark.asyncio
async def test_store_delete():
    """Testa delete de chave"""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_pool = AsyncDatabasePool(f"sqlite+aiosqlite:///{db_path}")
    await db_pool.initialize()
    await init_db(db_pool=db_pool)

    store = AsyncStateStore("5511999999999", db_pool)
    
    # Define valor
    await store.set("test_key", "test_value")
    
    # Deleta
    await store.delete("test_key")
    
    # Verifica que foi removido
    value = await store.get("test_key")
    assert value is None

    await db_pool.close()


@pytest.mark.asyncio
async def test_store_clear_cache():
    """Testa limpeza do cache (não remove do DB)"""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_pool = AsyncDatabasePool(f"sqlite+aiosqlite:///{db_path}")
    await db_pool.initialize()
    await init_db(db_pool=db_pool)

    store = AsyncStateStore("5511999999999", db_pool)
    
    # Define valores
    await store.set("key1", "value1")
    await store.set("key2", "value2")
    
    # Limpa
    await store.clear_cache()
    
    # Cache deve estar vazio, mas DB ainda deve conter os dados
    assert "key1" not in store._cache
    assert "key2" not in store._cache
    assert await store.get("key1") == "value1"
    assert await store.get("key2") == "value2"

    await db_pool.close()

