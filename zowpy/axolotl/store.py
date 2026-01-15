"""
Async Axolotl Store - Store totalmente assíncrono.

Todas operações DB são async (await, não bloqueiam).
Implementa todas as interfaces: SessionStore, PreKeyStore, SignedPreKeyStore, IdentityKeyStore.
"""

import asyncio
from typing import Optional, Dict, Any, List
from loguru import logger

from ..db.pool import AsyncDatabasePool
from .state.session_record import SessionRecord
from .state.prekey_record import PreKeyRecord
from .state.signed_prekey_record import SignedPreKeyRecord


class AsyncAxolotlStore:
    """
    Store Axolotl totalmente assíncrono.
    Todas operações DB são async (await, não bloqueiam).
    """
    
    def __init__(self, account_id: str, db_pool: AsyncDatabasePool):
        self.account_id = account_id
        self.db_pool = db_pool
        self._cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
    
    async def load_session(self, recipient_id: str, device_id: int = 0) -> Optional[Any]:
        """
        Carrega sessão de forma totalmente assíncrona.
        Await DB, não bloqueia.
        """
        cache_key = f"session:{recipient_id}:{device_id}"
        
        # Verifica cache
        async with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Busca no DB - await, não bloqueia
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchrow(
                    """
                    SELECT session_data FROM sessions
                    WHERE account_id = $1 AND recipient_id = $2 AND device_id = $3
                    """,
                    self.account_id,
                    recipient_id,
                    device_id
                )
            else:  # SQLite
                async with conn.execute(
                    """
                    SELECT session_data FROM sessions
                    WHERE account_id = ? AND recipient_id = ? AND device_id = ?
                    """,
                    (self.account_id, recipient_id, device_id)
                ) as cursor:
                    result = await cursor.fetchone()
        
        if result is None:
            return None
        
        # Deserializa sessão
        session_data = result[0] if isinstance(result, tuple) else result['session_data']
        session = self._deserialize_session(session_data)
        
        # Atualiza cache
        async with self._cache_lock:
            self._cache[cache_key] = session
        
        return session
    
    async def store_session(self, recipient_id: str, device_id: int, session: Any) -> None:
        """
        Armazena sessão de forma totalmente assíncrona.
        """
        session_data = self._serialize_session(session)
        
        # Salva no DB - await, não bloqueia
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO sessions (account_id, recipient_id, device_id, session_data)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (account_id, recipient_id, device_id)
                    DO UPDATE SET session_data = $4
                    """,
                    self.account_id,
                    recipient_id,
                    device_id,
                    session_data
                )
            else:  # SQLite
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions (account_id, recipient_id, device_id, session_data)
                    VALUES (?, ?, ?, ?)
                    """,
                    (self.account_id, recipient_id, device_id, session_data)
                )
                await conn.commit()
        
        # Atualiza cache
        cache_key = f"session:{recipient_id}:{device_id}"
        async with self._cache_lock:
            self._cache[cache_key] = session
    
    async def load_identity(self) -> Optional[Any]:
        """
        Carrega identidade de forma totalmente assíncrona.
        """
        cache_key = "identity"
        
        # Verifica cache
        async with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Busca no DB - await, não bloqueia
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchrow(
                    """
                    SELECT identity_data FROM identities
                    WHERE account_id = $1
                    """,
                    self.account_id
                )
            else:  # SQLite
                async with conn.execute(
                    """
                    SELECT identity_data FROM identities
                    WHERE account_id = ?
                    """,
                    (self.account_id,)
                ) as cursor:
                    result = await cursor.fetchone()
        
        if result is None:
            return None
        
        # Deserializa identidade
        identity_data = result[0] if isinstance(result, tuple) else result['identity_data']
        identity = self._deserialize_identity(identity_data)
        
        # Atualiza cache
        async with self._cache_lock:
            self._cache[cache_key] = identity
        
        return identity
    
    async def store_identity(self, identity: Any) -> None:
        """
        Armazena identidade de forma totalmente assíncrona.
        """
        identity_data = self._serialize_identity(identity)
        
        # Salva no DB - await, não bloqueia
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO identities (account_id, identity_data)
                    VALUES ($1, $2)
                    ON CONFLICT (account_id)
                    DO UPDATE SET identity_data = $2
                    """,
                    self.account_id,
                    identity_data
                )
            else:  # SQLite
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO identities (account_id, identity_data)
                    VALUES (?, ?)
                    """,
                    (self.account_id, identity_data)
                )
                await conn.commit()
        
        # Atualiza cache
        cache_key = "identity"
        async with self._cache_lock:
            self._cache[cache_key] = identity
    
    def _serialize_identity(self, identity: Any) -> bytes:
        """Serializa identidade"""
        return identity.serialize() if hasattr(identity, 'serialize') else bytes(identity)
    
    def _deserialize_identity(self, data: bytes) -> Any:
        """Deserializa identidade"""
        # Implementação específica
        return data
    
    def _serialize_session(self, session: Any) -> bytes:
        """Serializa sessão"""
        return session.serialize() if hasattr(session, 'serialize') else bytes(session)
    
    def _deserialize_session(self, data: bytes) -> SessionRecord:
        """Deserializa sessão"""
        return SessionRecord(serialized=data)
    
    # ========== SessionStore Methods ==========
    
    async def contains_session(self, recipient_id: str, device_id: int = 0) -> bool:
        """Verifica se contém sessão."""
        session = await self.load_session(recipient_id, device_id)
        return session is not None
    
    async def get_sub_device_sessions(self, recipient_id: str) -> List[int]:
        """Obtém lista de device IDs com sessões."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                results = await conn.fetch(
                    """
                    SELECT DISTINCT device_id FROM sessions
                    WHERE account_id = $1 AND recipient_id = $2
                    """,
                    self.account_id,
                    recipient_id,
                )
            else:
                async with conn.execute(
                    """
                    SELECT DISTINCT device_id FROM sessions
                    WHERE account_id = ? AND recipient_id = ?
                    """,
                    (self.account_id, recipient_id),
                ) as cursor:
                    results = await cursor.fetchall()
        
        return [row[0] if isinstance(row, tuple) else row["device_id"] for row in results]
    
    async def delete_session(self, recipient_id: str, device_id: int = 0) -> None:
        """Deleta sessão."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    DELETE FROM sessions
                    WHERE account_id = $1 AND recipient_id = $2 AND device_id = $3
                    """,
                    self.account_id,
                    recipient_id,
                    device_id,
                )
            else:
                await conn.execute(
                    """
                    DELETE FROM sessions
                    WHERE account_id = ? AND recipient_id = ? AND device_id = ?
                    """,
                    (self.account_id, recipient_id, device_id),
                )
                await conn.commit()
        
        # Remove do cache
        cache_key = f"session:{recipient_id}:{device_id}"
        async with self._cache_lock:
            self._cache.pop(cache_key, None)
    
    async def delete_all_sessions(self, recipient_id: str) -> None:
        """Deleta todas sessões de um recipient."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    DELETE FROM sessions
                    WHERE account_id = $1 AND recipient_id = $2
                    """,
                    self.account_id,
                    recipient_id,
                )
            else:
                await conn.execute(
                    """
                    DELETE FROM sessions
                    WHERE account_id = ? AND recipient_id = ?
                    """,
                    (self.account_id, recipient_id),
                )
                await conn.commit()
        
        # Remove do cache
        async with self._cache_lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(f"session:{recipient_id}:")
            ]
            for key in keys_to_remove:
                del self._cache[key]
    
    # ========== PreKeyStore Methods ==========
    
    async def load_prekey(self, prekey_id: int) -> Optional[PreKeyRecord]:
        """Carrega prekey."""
        cache_key = f"prekey:{prekey_id}"
        
        async with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchrow(
                    """
                    SELECT prekey_data FROM prekeys
                    WHERE account_id = $1 AND prekey_id = $2
                    """,
                    self.account_id,
                    prekey_id,
                )
            else:
                async with conn.execute(
                    """
                    SELECT prekey_data FROM prekeys
                    WHERE account_id = ? AND prekey_id = ?
                    """,
                    (self.account_id, prekey_id),
                ) as cursor:
                    result = await cursor.fetchone()
        
        if result is None:
            return None
        
        prekey_data = result[0] if isinstance(result, tuple) else result["prekey_data"]
        prekey = PreKeyRecord(prekey_id, None, serialized=prekey_data)
        
        async with self._cache_lock:
            self._cache[cache_key] = prekey
        
        return prekey
    
    async def store_prekey(self, prekey_id: int, prekey_record: PreKeyRecord) -> None:
        """Armazena prekey."""
        prekey_data = prekey_record.serialize()
        
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO prekeys (account_id, prekey_id, prekey_data)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (account_id, prekey_id)
                    DO UPDATE SET prekey_data = $3
                    """,
                    self.account_id,
                    prekey_id,
                    prekey_data,
                )
            else:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO prekeys (account_id, prekey_id, prekey_data)
                    VALUES (?, ?, ?)
                    """,
                    (self.account_id, prekey_id, prekey_data),
                )
                await conn.commit()
        
        cache_key = f"prekey:{prekey_id}"
        async with self._cache_lock:
            self._cache[cache_key] = prekey_record
    
    async def contains_prekey(self, prekey_id: int) -> bool:
        """Verifica se contém prekey."""
        prekey = await self.load_prekey(prekey_id)
        return prekey is not None
    
    async def remove_prekey(self, prekey_id: int) -> None:
        """Remove prekey."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    DELETE FROM prekeys
                    WHERE account_id = $1 AND prekey_id = $2
                    """,
                    self.account_id,
                    prekey_id,
                )
            else:
                await conn.execute(
                    """
                    DELETE FROM prekeys
                    WHERE account_id = ? AND prekey_id = ?
                    """,
                    (self.account_id, prekey_id),
                )
                await conn.commit()
        
        cache_key = f"prekey:{prekey_id}"
        async with self._cache_lock:
            self._cache.pop(cache_key, None)
    
    async def load_prekeys(self) -> List[PreKeyRecord]:
        """Carrega todos os prekeys pendentes."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                results = await conn.fetch(
                    """
                    SELECT prekey_data FROM prekeys
                    WHERE account_id = $1
                    ORDER BY prekey_id
                    """,
                    self.account_id,
                )
            else:
                async with conn.execute(
                    """
                    SELECT prekey_data FROM prekeys
                    WHERE account_id = ?
                    ORDER BY prekey_id
                    """,
                    (self.account_id,),
                ) as cursor:
                    results = await cursor.fetchall()
        
        prekeys = []
        for row in results:
            data = row[0] if isinstance(row, tuple) else row["prekey_data"]
            # Extrai prekey_id do banco (precisa ser ajustado conforme estrutura)
            # Por enquanto, tenta deserializar
            prekey = PreKeyRecord(0, None, serialized=data)
            prekeys.append(prekey)
        
        return prekeys
    
    async def load_unsent_prekeys(self) -> List[PreKeyRecord]:
        """Carrega prekeys não enviados (pendentes)."""
        # Por enquanto, retorna todos os prekeys
        # Pode ser melhorado para marcar quais foram enviados
        return await self.load_prekeys()
    
    async def set_prekeys_as_sent(self, prekey_ids: List[int]) -> None:
        """
        Marca prekeys como enviados.
        
        :param prekey_ids: Lista de IDs de prekeys
        """
        # Por enquanto, apenas loga
        # Pode ser implementado com uma coluna 'sent' na tabela
        logger.debug(f"Marking {len(prekey_ids)} prekeys as sent")
    
    async def load_max_prekey_id(self) -> int:
        """Obtém o maior ID de prekey."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchval(
                    """
                    SELECT MAX(prekey_id) FROM prekeys
                    WHERE account_id = $1
                    """,
                    self.account_id,
                )
            else:
                async with conn.execute(
                    """
                    SELECT MAX(prekey_id) FROM prekeys
                    WHERE account_id = ?
                    """,
                    (self.account_id,),
                ) as cursor:
                    result = await cursor.fetchone()
                    result = result[0] if result else None
        
        return result if result is not None else 0
    
    # ========== SignedPreKeyStore Methods ==========
    
    async def load_signed_prekey(self, signed_prekey_id: int) -> Optional[SignedPreKeyRecord]:
        """Carrega signed prekey."""
        cache_key = f"signed_prekey:{signed_prekey_id}"
        
        async with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchrow(
                    """
                    SELECT signed_prekey_data FROM signed_prekeys
                    WHERE account_id = $1 AND signed_prekey_id = $2
                    """,
                    self.account_id,
                    signed_prekey_id,
                )
            else:
                async with conn.execute(
                    """
                    SELECT signed_prekey_data FROM signed_prekeys
                    WHERE account_id = ? AND signed_prekey_id = ?
                    """,
                    (self.account_id, signed_prekey_id),
                ) as cursor:
                    result = await cursor.fetchone()
        
        if result is None:
            return None
        
        signed_prekey_data = (
            result[0]
            if isinstance(result, tuple)
            else result["signed_prekey_data"]
        )
        signed_prekey = SignedPreKeyRecord(
            0, 0, None, b"", serialized=signed_prekey_data
        )
        
        async with self._cache_lock:
            self._cache[cache_key] = signed_prekey
        
        return signed_prekey
    
    async def load_signed_prekeys(self) -> List[SignedPreKeyRecord]:
        """Carrega todos signed prekeys."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                results = await conn.fetch(
                    """
                    SELECT signed_prekey_data FROM signed_prekeys
                    WHERE account_id = $1
                    """,
                    self.account_id,
                )
            else:
                async with conn.execute(
                    """
                    SELECT signed_prekey_data FROM signed_prekeys
                    WHERE account_id = ?
                    """,
                    (self.account_id,),
                ) as cursor:
                    results = await cursor.fetchall()
        
        signed_prekeys = []
        for row in results:
            data = row[0] if isinstance(row, tuple) else row["signed_prekey_data"]
            signed_prekeys.append(SignedPreKeyRecord(0, 0, None, b"", serialized=data))
        
        return signed_prekeys
    
    async def store_signed_prekey(
        self, signed_prekey_id: int, signed_prekey_record: SignedPreKeyRecord
    ) -> None:
        """Armazena signed prekey."""
        signed_prekey_data = signed_prekey_record.serialize()
        
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO signed_prekeys (account_id, signed_prekey_id, signed_prekey_data)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (account_id, signed_prekey_id)
                    DO UPDATE SET signed_prekey_data = $3
                    """,
                    self.account_id,
                    signed_prekey_id,
                    signed_prekey_data,
                )
            else:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO signed_prekeys (account_id, signed_prekey_id, signed_prekey_data)
                    VALUES (?, ?, ?)
                    """,
                    (self.account_id, signed_prekey_id, signed_prekey_data),
                )
                await conn.commit()
        
        cache_key = f"signed_prekey:{signed_prekey_id}"
        async with self._cache_lock:
            self._cache[cache_key] = signed_prekey_record
    
    async def contains_signed_prekey(self, signed_prekey_id: int) -> bool:
        """Verifica se contém signed prekey."""
        signed_prekey = await self.load_signed_prekey(signed_prekey_id)
        return signed_prekey is not None
    
    async def remove_signed_prekey(self, signed_prekey_id: int) -> None:
        """Remove signed prekey."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    DELETE FROM signed_prekeys
                    WHERE account_id = $1 AND signed_prekey_id = $2
                    """,
                    self.account_id,
                    signed_prekey_id,
                )
            else:
                await conn.execute(
                    """
                    DELETE FROM signed_prekeys
                    WHERE account_id = ? AND signed_prekey_id = ?
                    """,
                    (self.account_id, signed_prekey_id),
                )
                await conn.commit()
        
        cache_key = f"signed_prekey:{signed_prekey_id}"
        async with self._cache_lock:
            self._cache.pop(cache_key, None)
    
    # ========== IdentityKeyStore Methods ==========
    
    async def load_identity(self, recipient_id: str = "local", device_id: int = 0):
        """Carrega identidade."""
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchrow(
                    """
                    SELECT identity_data FROM identities
                    WHERE account_id = $1 AND recipient_id = $2 AND device_id = $3
                    """,
                    self.account_id,
                    recipient_id,
                    device_id,
                )
            else:
                async with conn.execute(
                    """
                    SELECT identity_data FROM identities
                    WHERE account_id = ? AND recipient_id = ? AND device_id = ?
                    """,
                    (self.account_id, recipient_id, device_id),
                ) as cursor:
                    result = await cursor.fetchone()
        
        if result is None:
            return None
        
        identity_data = result[0] if isinstance(result, tuple) else result["identity_data"]
        
        # Deserializa IdentityKeyPair
        from ..axolotl.crypto import IdentityKeyPair
        # Por enquanto retorna os dados brutos, precisa deserializar corretamente
        return identity_data
    
    async def get_identity_key_pair(self):
        """Obtém par de chaves de identidade."""
        identity_data = await self.load_identity()
        if identity_data is None:
            return None
        # Por enquanto retorna os dados, precisa deserializar para IdentityKeyPair
        # Isso será implementado quando necessário
        return identity_data
    
    async def get_local_registration_id(self) -> Optional[int]:
        """Obtém registration ID local."""
        identity = await self.load_identity()
        if identity is None:
            return None
        # Registration ID pode estar armazenado separadamente
        # Por enquanto retorna None, precisa ser implementado
        return None
    
    async def save_local_registration_id(self, registration_id: int) -> None:
        """Salva registration ID local."""
        # Salva junto com identity key pair
        identity_key_pair = await self.get_identity_key_pair()
        if identity_key_pair:
            # Atualiza identity com registration ID
            await self.save_identity_key_pair(identity_key_pair, registration_id)
        else:
            # Se não tem identity key pair, cria um registro mínimo
            async with self.db_pool.acquire() as conn:
                if self.db_pool._db_type == "postgresql":
                    await conn.execute(
                        """
                        INSERT INTO identities (account_id, recipient_id, device_id, identity_data, registration_id)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (account_id, recipient_id, device_id)
                        DO UPDATE SET registration_id = $5
                        """,
                        self.account_id,
                        "local",
                        0,
                        b"",
                        registration_id,
                    )
                else:
                    await conn.execute(
                        """
                        INSERT OR REPLACE INTO identities (account_id, recipient_id, device_id, identity_data, registration_id)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (self.account_id, "local", 0, b"", registration_id),
                    )
                    await conn.commit()
    
    async def save_identity_key_pair(self, identity_key_pair, registration_id: Optional[int] = None) -> None:
        """Salva par de chaves de identidade."""
        identity_data = identity_key_pair.serialize_public() if hasattr(identity_key_pair, 'serialize_public') else bytes(identity_key_pair)
        
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO identities (account_id, recipient_id, device_id, identity_data, registration_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (account_id, recipient_id, device_id)
                    DO UPDATE SET identity_data = $4, registration_id = COALESCE($5, identities.registration_id)
                    """,
                    self.account_id,
                    "local",
                    0,
                    identity_data,
                    registration_id,
                )
            else:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO identities (account_id, recipient_id, device_id, identity_data, registration_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (self.account_id, "local", 0, identity_data, registration_id),
                )
                await conn.commit()
    
    async def save_identity(
        self, recipient_id: str, device_id: int, identity_key
    ) -> None:
        """Salva chave de identidade."""
        # Salva identidade remota
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO identities (account_id, recipient_id, device_id, identity_data)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (account_id, recipient_id, device_id)
                    DO UPDATE SET identity_data = $4
                    """,
                    self.account_id,
                    recipient_id,
                    device_id,
                    identity_key.serialize() if hasattr(identity_key, "serialize") else bytes(identity_key),
                )
            else:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO identities (account_id, recipient_id, device_id, identity_data)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        self.account_id,
                        recipient_id,
                        device_id,
                        identity_key.serialize() if hasattr(identity_key, "serialize") else bytes(identity_key),
                    ),
                )
                await conn.commit()
    
    async def is_trusted_identity(
        self, recipient_id: str, device_id: int, identity_key
    ) -> bool:
        """Verifica se identidade é confiável."""
        # Por padrão, confia em todas identidades
        # Pode ser customizado para verificar contra identidades salvas
        return True
    
    async def update_local_identity_keys(
        self,
        registration_id: int,
        public_key: bytes,
        private_key: bytes,
        device_id: int = 0
    ) -> None:
        """
        Atualiza chaves de identidade locais (usado em import flows).
        
        :param registration_id: Registration ID
        :param public_key: Chave pública
        :param private_key: Chave privada
        :param device_id: ID do dispositivo
        """
        # Serializa chaves (public_key já deve ter o byte de tipo 0x05)
        identity_data = public_key + private_key
        
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO identities (account_id, recipient_id, device_id, identity_data, registration_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (account_id, recipient_id, device_id)
                    DO UPDATE SET identity_data = $4, registration_id = $5
                    """,
                    self.account_id,
                    "local",
                    device_id,
                    identity_data,
                    registration_id,
                )
            else:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO identities (account_id, recipient_id, device_id, identity_data, registration_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (self.account_id, "local", device_id, identity_data, registration_id),
                )
                await conn.commit()

