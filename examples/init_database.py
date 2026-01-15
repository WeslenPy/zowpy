"""
Exemplo de inicialização de banco de dados.

Demonstra como criar todas as tabelas do banco de dados.
"""

import asyncio
from zowpy.db import init_db, init_db_from_url, AsyncDatabasePool


async def example_init_from_url():
    """Exemplo usando URL diretamente"""
    print("=== Inicializando banco a partir de URL ===")
    
    # Usa settings como padrão
    await init_db_from_url(settings.zowpy_db_url)
    print(f"✅ Banco inicializado: {settings.zowpy_db_url}")
    
    # PostgreSQL (se configurado)
    # await init_db_from_url("postgresql+asyncpg://user:pass@localhost/zowpy")


async def example_init_from_pool():
    """Exemplo usando pool existente"""
    print("=== Inicializando banco a partir de pool ===")
    
    # Cria pool usando settings
    db_pool = AsyncDatabasePool(settings.zowpy_db_url)
    await db_pool.initialize()
    
    try:
        # Inicializa banco
        await init_db(db_pool=db_pool)
        print("✅ Banco inicializado via pool")
    finally:
        await db_pool.close()


async def example_init_drop_existing():
    """Exemplo dropando tabelas existentes (perigoso!)"""
    print("=== Inicializando banco dropando tabelas existentes ===")
    
    # ⚠️ CUIDADO: Isso remove todos os dados!
    await init_db_from_url(
        settings.zowpy_db_url,
        drop_existing=True
    )
    print("✅ Banco reinicializado (tabelas antigas removidas)")


async def main():
    """Executa todos os exemplos"""
    await example_init_from_url()
    print()
    await example_init_from_pool()
    print()
    # Descomente para testar drop_existing
    # await example_init_drop_existing()


if __name__ == "__main__":
    asyncio.run(main())

