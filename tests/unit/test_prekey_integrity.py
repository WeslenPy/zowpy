"""
Teste de integridade de PreKeys: geração, armazenamento e recuperação.

Valida que após gerar uma prekey, salvá-la no banco e recuperá-la,
ela ainda é idêntica à original.
"""

import pytest
import tempfile
import os
from zowpy.db.pool import AsyncDatabasePool
from zowpy.db import init_db
from zowpy.db.store.sqlaxolotlstore import SqlAxolotlStore
from zowpy.axolotl.util.keyhelper import KeyHelper
from zowpy.axolotl.state.prekeyrecord import PreKeyRecord


@pytest.fixture
async def db_pool():
    """Fixture que cria um banco de dados temporário para os testes"""
    # Usa arquivo temporário (in-memory pode ter problemas com sessões async)
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = temp_file.name
    temp_file.close()
    
    db_pool = AsyncDatabasePool(f"sqlite+aiosqlite:///{db_path}")
    await db_pool.initialize()
    await init_db(db_pool=db_pool)
    
    yield db_pool
    
    # Cleanup
    await db_pool.close()
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
async def axolotl_store(db_pool):
    """Fixture que cria um SqlAxolotlStore para os testes"""
    account_id = "5511999999999"
    
    # Cria store (ele vai criar a conta automaticamente quando necessário)
    store = SqlAxolotlStore(account_id, db_pool)
    
    yield store


@pytest.mark.asyncio
async def test_prekey_integrity_individual_store(axolotl_store):
    """
    Testa que uma prekey gerada, salva individualmente e recuperada
    permanece idêntica à original.
    """
    # 1. Gera uma prekey
    prekeys = KeyHelper.generatePreKeys(1, 1)
    assert len(prekeys) == 1
    
    original_prekey = prekeys[0]
    prekey_id = original_prekey.getId()
    
    # Validações da prekey original
    original_key_pair = original_prekey.getKeyPair()
    original_public_key = original_key_pair.getPublicKey()
    original_private_key = original_key_pair.getPrivateKey()
    original_serialized = original_prekey.serialize()
    
    # Logs para debug
    print(f"\n[TEST] Prekey original gerada:")
    print(f"  - ID: {prekey_id}")
    print(f"  - Serialized size: {len(original_serialized)} bytes")
    print(f"  - Public key size: {len(original_public_key.serialize())} bytes")
    print(f"  - Private key size: {len(original_private_key.serialize())} bytes")
    
    # 2. Salva no banco usando storePreKey individual
    await axolotl_store.storePreKey(prekey_id, original_prekey)
    
    # 3. Recupera do banco
    loaded_prekey = await axolotl_store.loadPreKey(prekey_id)
    
    # 4. Validações
    # 4.1: ID deve ser o mesmo
    assert loaded_prekey.getId() == prekey_id, "Prekey ID não corresponde"
    
    # 4.2: Serialização deve ser idêntica
    loaded_serialized = loaded_prekey.serialize()
    assert loaded_serialized == original_serialized, (
        f"Serialização não corresponde!\n"
        f"Original: {len(original_serialized)} bytes, hash={hash(original_serialized)}\n"
        f"Loaded: {len(loaded_serialized)} bytes, hash={hash(loaded_serialized)}\n"
        f"Primeiros 20 bytes original: {original_serialized[:20].hex()}\n"
        f"Primeiros 20 bytes loaded: {loaded_serialized[:20].hex()}"
    )
    
    # 4.3: KeyPair deve ser idêntico
    loaded_key_pair = loaded_prekey.getKeyPair()
    loaded_public_key = loaded_key_pair.getPublicKey()
    loaded_private_key = loaded_key_pair.getPrivateKey()
    
    original_public_serialized = original_public_key.serialize()
    loaded_public_serialized = loaded_public_key.serialize()
    assert loaded_public_serialized == original_public_serialized, (
        f"Public key não corresponde!\n"
        f"Original: {original_public_serialized.hex()}\n"
        f"Loaded: {loaded_public_serialized.hex()}"
    )
    
    original_private_serialized = original_private_key.serialize()
    loaded_private_serialized = loaded_private_key.serialize()
    assert loaded_private_serialized == original_private_serialized, (
        f"Private key não corresponde!\n"
        f"Original: {original_private_serialized.hex()}\n"
        f"Loaded: {loaded_private_serialized.hex()}"
    )
    
    # 4.4: PreKeyRecord deve poder ser recriado corretamente
    recreated_prekey = PreKeyRecord(serialized=loaded_serialized)
    assert recreated_prekey.getId() == prekey_id
    assert recreated_prekey.serialize() == original_serialized
    
    print(f"\n[TEST] ✓ Prekey individual: INTEGRIDADE VALIDADA")


@pytest.mark.asyncio
async def test_prekey_integrity_bulk_store(axolotl_store):
    """
    Testa que prekeys geradas, salvas em bulk e recuperadas
    permanecem idênticas às originais.
    
    Este teste verifica se há corrupção no bulk insert.
    """
    # 1. Gera múltiplas prekeys
    count = 10
    prekeys = KeyHelper.generatePreKeys(100, count)
    assert len(prekeys) == count
    
    # Armazena informações originais
    original_data = {}
    for prekey in prekeys:
        prekey_id = prekey.getId()
        original_data[prekey_id] = {
            'prekey': prekey,
            'serialized': prekey.serialize(),
            'key_pair': prekey.getKeyPair(),
            'public_key': prekey.getKeyPair().getPublicKey().serialize(),
            'private_key': prekey.getKeyPair().getPrivateKey().serialize(),
        }
    
    print(f"\n[TEST] Geradas {count} prekeys para teste de bulk insert")
    
    # 2. Prepara tuplas para bulk insert
    prekey_tuples = [(key.getId(), key) for key in prekeys]
    
    # 3. Salva todas em bulk
    await axolotl_store.storePreKeys(prekey_tuples)
    
    print(f"[TEST] Prekeys salvas em bulk")
    
    # 4. Recupera e valida cada uma
    for prekey_id, original_info in original_data.items():
        loaded_prekey = await axolotl_store.loadPreKey(prekey_id)
        
        # Valida ID
        assert loaded_prekey.getId() == prekey_id, f"Prekey {prekey_id}: ID não corresponde"
        
        # Valida serialização
        loaded_serialized = loaded_prekey.serialize()
        original_serialized = original_info['serialized']
        
        assert loaded_serialized == original_serialized, (
            f"Prekey {prekey_id}: Serialização não corresponde!\n"
            f"  Original: {len(original_serialized)} bytes, hash={hash(original_serialized)}\n"
            f"  Loaded: {len(loaded_serialized)} bytes, hash={hash(loaded_serialized)}\n"
            f"  Primeiros 20 bytes original: {original_serialized[:20].hex()}\n"
            f"  Primeiros 20 bytes loaded: {loaded_serialized[:20].hex()}\n"
            f"  Últimos 20 bytes original: {original_serialized[-20:].hex()}\n"
            f"  Últimos 20 bytes loaded: {loaded_serialized[-20:].hex()}"
        )
        
        # Valida KeyPair
        loaded_key_pair = loaded_prekey.getKeyPair()
        loaded_public_key = loaded_key_pair.getPublicKey().serialize()
        loaded_private_key = loaded_key_pair.getPrivateKey().serialize()
        
        assert loaded_public_key == original_info['public_key'], (
            f"Prekey {prekey_id}: Public key não corresponde"
        )
        
        assert loaded_private_key == original_info['private_key'], (
            f"Prekey {prekey_id}: Private key não corresponde"
        )
        
        # Valida que pode ser recriada
        recreated = PreKeyRecord(serialized=loaded_serialized)
        assert recreated.getId() == prekey_id
        assert recreated.serialize() == original_serialized
        
        print(f"  ✓ Prekey {prekey_id}: OK")
    
    print(f"\n[TEST] ✓ Todas as {count} prekeys em bulk: INTEGRIDADE VALIDADA")


@pytest.mark.asyncio
async def test_prekey_byte_level_comparison(axolotl_store):
    """
    Teste detalhado comparando byte a byte para detectar
    qualquer corrupção mínima.
    """
    # Gera uma prekey
    prekeys = KeyHelper.generatePreKeys(999, 1)
    original_prekey = prekeys[0]
    prekey_id = original_prekey.getId()
    
    original_serialized = original_prekey.serialize()
    original_bytes = bytes(original_serialized)
    
    print(f"\n[TEST] Teste byte-level comparison")
    print(f"  Prekey ID: {prekey_id}")
    print(f"  Tamanho: {len(original_bytes)} bytes")
    print(f"  Hash original: {hash(original_bytes)}")
    
    # Salva
    await axolotl_store.storePreKey(prekey_id, original_prekey)
    
    # Recupera
    loaded_prekey = await axolotl_store.loadPreKey(prekey_id)
    loaded_serialized = loaded_prekey.serialize()
    loaded_bytes = bytes(loaded_serialized)
    
    print(f"  Hash loaded: {hash(loaded_bytes)}")
    
    # Comparação byte a byte
    if original_bytes != loaded_bytes:
        # Encontra primeira diferença
        min_len = min(len(original_bytes), len(loaded_bytes))
        for i in range(min_len):
            if original_bytes[i] != loaded_bytes[i]:
                print(f"\n  ERRO: Primeira diferença no byte {i}:")
                print(f"    Original: 0x{original_bytes[i]:02x}")
                print(f"    Loaded: 0x{loaded_bytes[i]:02x}")
                print(f"    Contexto (10 bytes antes/depois):")
                start = max(0, i - 10)
                end = min(len(original_bytes), i + 11)
                print(f"    Original: {original_bytes[start:end].hex()}")
                print(f"    Loaded:   {loaded_bytes[start:end].hex()}")
                break
        
        if len(original_bytes) != len(loaded_bytes):
            print(f"  ERRO: Tamanhos diferentes!")
            print(f"    Original: {len(original_bytes)} bytes")
            print(f"    Loaded: {len(loaded_bytes)} bytes")
        
        assert False, "Bytes não correspondem exatamente!"
    
    assert original_bytes == loaded_bytes, "Falha na comparação byte a byte"
    print(f"  ✓ Comparação byte a byte: OK")


@pytest.mark.asyncio
async def test_prekey_bulk_vs_individual_consistency(axolotl_store):
    """
    Testa que prekeys salvas individualmente e em bulk
    produzem resultados idênticos quando recuperadas.
    """
    # Gera prekeys
    prekeys = KeyHelper.generatePreKeys(200, 5)
    
    # Separa: 3 para individual, 2 para bulk
    individual_prekeys = prekeys[:3]
    bulk_prekeys = prekeys[3:]
    
    # Salva individuais
    for prekey in individual_prekeys:
        await axolotl_store.storePreKey(prekey.getId(), prekey)
    
    # Salva em bulk
    bulk_tuples = [(key.getId(), key) for key in bulk_prekeys]
    await axolotl_store.storePreKeys(bulk_tuples)
    
    # Recupera todas e valida
    all_prekeys = individual_prekeys + bulk_prekeys
    
    for original_prekey in all_prekeys:
        prekey_id = original_prekey.getId()
        loaded_prekey = await axolotl_store.loadPreKey(prekey_id)
        
        original_serialized = original_prekey.serialize()
        loaded_serialized = loaded_prekey.serialize()
        
        assert original_serialized == loaded_serialized, (
            f"Prekey {prekey_id}: Diferença entre método de armazenamento"
        )
    
    print(f"\n[TEST] ✓ Consistência entre bulk e individual: OK")

