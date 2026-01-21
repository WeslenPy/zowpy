"""
Async State Store - Store unificado para estado da conta.

Cache assíncrono e integração DB.
"""

import asyncio
import time
import json
from typing import Optional, Dict, Any
from loguru import logger

from zowpy.db.config.engine import AsyncSessionMaker

class AsyncStateStore:
    """
    Store unificado para todo estado da conta.
    Cache em memória com TTL, integração com DB assíncrono.
    """
    
    def __init__(self, account_id: str, session_maker: AsyncSessionMaker):
        self.account_id = account_id
        self.session_maker = session_maker
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._cache_lock = asyncio.Lock()
        self._default_ttl = 300  # 5 minutos
    
    async def get_identity(self) -> Optional[Any]:
        """
        Obtém identidade de forma totalmente assíncrona.
        Await DB, não bloqueia.
        
        Returns:
            Identity ou None
        """
        cache_key = "identity"
        
        # Verifica cache primeiro
        async with self._cache_lock:
            if cache_key in self._cache:
                ttl = self._cache_ttl.get(cache_key, 0)
                if time.time() < ttl:
                    return self._cache[cache_key]
        
        # Busca no DB - await, não bloqueia
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchrow(
                    """
                    SELECT identity_data FROM axolotl_identities
                    WHERE account_id = $1 AND recipient_id = $2 AND device_id = $3
                    """,
                    self.account_id,
                    "local",
                    0
                )
            else:  # SQLite
                async with conn.execute(
                    """
                    SELECT identity_data FROM axolotl_identities
                    WHERE account_id = ? AND recipient_id = ? AND device_id = ?
                    """,
                    (self.account_id, "local", 0)
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
            self._cache_ttl[cache_key] = time.time() + self._default_ttl
        
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
                    INSERT INTO axolotl_identities (account_id, recipient_id, device_id, identity_data)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (account_id, recipient_id, device_id)
                    DO UPDATE SET identity_data = $4
                    """,
                    self.account_id,
                    "local",
                    0,
                    identity_data
                )
            else:  # SQLite
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO axolotl_identities (account_id, recipient_id, device_id, identity_data)
                    VALUES (?, ?, ?, ?)
                    """,
                    (self.account_id, "local", 0, identity_data)
                )
                await conn.commit()
        
        # Atualiza cache
        cache_key = "identity"
        async with self._cache_lock:
            self._cache[cache_key] = identity
            self._cache_ttl[cache_key] = time.time() + self._default_ttl
    
    async def get_session(self, recipient_id: str) -> Optional[Any]:
        """
        Obtém sessão de forma totalmente assíncrona.
        Await DB, não bloqueia.
        """
        cache_key = f"session:{recipient_id}"
        
        # Verifica cache
        async with self._cache_lock:
            if cache_key in self._cache:
                ttl = self._cache_ttl.get(cache_key, 0)
                if time.time() < ttl:
                    return self._cache[cache_key]
        
        # Busca no DB - await, não bloqueia
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                result = await conn.fetchrow(
                    """
                    SELECT session_data FROM axolotl_sessions
                    WHERE account_id = $1 AND recipient_id = $2 AND device_id = $3
                    """,
                    self.account_id,
                    recipient_id,
                    0
                )
            else:  # SQLite
                async with conn.execute(
                    """
                    SELECT session_data FROM axolotl_sessions
                    WHERE account_id = ? AND recipient_id = ? AND device_id = ?
                    """,
                    (self.account_id, recipient_id, 0)
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
            self._cache_ttl[cache_key] = time.time() + self._default_ttl
        
        return session
    
    async def store_session(self, recipient_id: str, session: Any) -> None:
        """
        Armazena sessão de forma totalmente assíncrona.
        """
        session_data = self._serialize_session(session)
        
        # Salva no DB - await, não bloqueia
        async with self.db_pool.acquire() as conn:
            if self.db_pool._db_type == "postgresql":
                await conn.execute(
                    """
                    INSERT INTO axolotl_sessions (account_id, recipient_id, device_id, session_data)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (account_id, recipient_id, device_id)
                    DO UPDATE SET session_data = $4
                    """,
                    self.account_id,
                    recipient_id,
                    0,
                    session_data
                )
            else:  # SQLite
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO axolotl_sessions (account_id, recipient_id, device_id, session_data)
                    VALUES (?, ?, ?, ?)
                    """,
                    (self.account_id, recipient_id, 0, session_data)
                )
                await conn.commit()
        
        # Atualiza cache
        cache_key = f"session:{recipient_id}"
        async with self._cache_lock:
            self._cache[cache_key] = session
            self._cache_ttl[cache_key] = time.time() + self._default_ttl
    
    def _serialize_identity(self, identity: Any) -> bytes:
        """Serializa identidade"""
        # Implementação específica
        return identity.serialize() if hasattr(identity, 'serialize') else bytes(identity)
    
    def _deserialize_identity(self, data: bytes) -> Any:
        """Deserializa identidade"""
        # Implementação específica
        # Por enquanto retorna dados brutos
        return data
    
    def _serialize_session(self, session: Any) -> bytes:
        """Serializa sessão"""
        return session.serialize() if hasattr(session, 'serialize') else bytes(session)
    
    def _deserialize_session(self, data: bytes) -> Any:
        """Deserializa sessão"""
        # Implementação específica
        return data
    
    async def clear_cache(self) -> None:
        """Limpa cache de forma assíncrona"""
        async with self._cache_lock:
            self._cache.clear()
            self._cache_ttl.clear()
    
    # ========== Métodos genéricos para qualquer chave ==========
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Obtém valor genérico de forma totalmente assíncrona.
        
        :param key: Chave do valor
        :return: Valor ou None
        """
        # Verifica cache primeiro
        async with self._cache_lock:
            if key in self._cache:
                ttl = self._cache_ttl.get(key, 0)
                if time.time() < ttl:
                    return self._cache[key]
        
        # Busca no DB usando SQLAlchemy
        from ..db.models import Account, AccountState
        from sqlalchemy import select
        
        async with self.session_maker() as session:
            # Primeiro obtém Account pelo phone
            result = await session.execute(select(Account).filter_by(phone=self.account_id))
            account = result.scalar_one_or_none()
            
            if not account:
                return None
            
            # Busca AccountState
            result = await session.execute(
                select(AccountState).filter_by(
                    account_id=account.id,
                    key=key
                )
            )
            account_state = result.scalar_one_or_none()
            
            if account_state is None or not account_state.value:
                return None
            
            # Deserializa valor
            value = json.loads(account_state.value) if account_state.value else None
        
        # Atualiza cache
        async with self._cache_lock:
            self._cache[key] = value
            self._cache_ttl[key] = time.time() + self._default_ttl
        
        return value
    
    async def set(self, key: str, value: Any) -> None:
        """
        Armazena valor genérico de forma totalmente assíncrona.
        
        :param key: Chave do valor
        :param value: Valor para armazenar
        """
        # Serializa valor
        value_json = json.dumps(value) if value is not None else None
        
        # Salva no DB usando SQLAlchemy
        from ..db.models import Account, AccountState
        from sqlalchemy import select
        
        async with self.session_maker() as session:
            # Primeiro obtém Account pelo phone
            result = await session.execute(select(Account).filter_by(phone=self.account_id))
            account = result.scalar_one_or_none()
            
            if not account:
                # Cria Account se não existir
                account = Account(phone=self.account_id)
                session.add(account)
                await session.flush()
            
            # Busca ou cria AccountState
            result = await session.execute(
                select(AccountState).filter_by(
                    account_id=account.id,
                    key=key
                )
            )
            account_state = result.scalar_one_or_none()
            
            if account_state is None:
                account_state = AccountState(
                    account_id=account.id,
                    key=key,
                    value=value_json
                )
                session.add(account_state)
            else:
                account_state.value = value_json
            
            await session.commit()
        
        # Atualiza cache
        async with self._cache_lock:
            self._cache[key] = value
            self._cache_ttl[key] = time.time() + self._default_ttl
    
    async def delete(self, key: str) -> None:
        """
        Remove valor genérico de forma totalmente assíncrona.
        
        :param key: Chave do valor
        """
        # Remove do DB usando SQLAlchemy
        from ..db.models import Account, AccountState
        from sqlalchemy import select
        
        async with self.session_maker() as session:
            # Primeiro obtém Account pelo phone
            result = await session.execute(select(Account).filter_by(phone=self.account_id))
            account = result.scalar_one_or_none()
            
            if not account:
                return
            
            # Busca e remove AccountState
            result = await session.execute(
                select(AccountState).filter_by(
                    account_id=account.id,
                    key=key
                )
            )
            account_state = result.scalar_one_or_none()
            
            if account_state:
                # Remove objeto da sessão (SQLAlchemy 2.0)
                session.delete(account_state)
                await session.commit()
        
        # Remove do cache
        async with self._cache_lock:
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)
    
    # ========== Métodos específicos para credenciais ==========
    
    async def get_username(self) -> Optional[str]:
        """Obtém username."""
        return await self.get("username")
    
    async def set_username(self, username: str) -> None:
        """Define username."""
        await self.set("username", username)
    
    async def get_password(self) -> Optional[str]:
        """Obtém password/token."""
        return await self.get("password")
    
    async def set_password(self, password: str) -> None:
        """Define password/token."""
        await self.set("password", password)
    
    async def get_registration_id(self) -> Optional[int]:
        """Obtém registration ID."""
        reg_id = await self.get("registration_id")
        return int(reg_id) if reg_id is not None else None
    
    async def set_registration_id(self, registration_id: int) -> None:
        """Define registration ID."""
        await self.set("registration_id", registration_id)
    
    async def get_device_id(self) -> Optional[int]:
        """Obtém device ID."""
        device_id = await self.get("device_id")
        return int(device_id) if device_id is not None else None
    
    async def set_device_id(self, device_id: int) -> None:
        """Define device ID."""
        await self.set("device_id", device_id)
