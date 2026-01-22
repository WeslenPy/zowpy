"""
Account Manager - Gerenciador de múltiplas contas.

Gerencia múltiplos ZowPyClient de forma assíncrona.
"""

import asyncio
from typing import Dict, Optional
from loguru import logger

from zowpy.db.config.engine import AsyncSessionMaker

from .client import ZowPyClient


class AccountManager:
    """
    Gerenciador de múltiplas contas.
    Gerencia múltiplos ZowPyClient de forma assíncrona.
    """
    
    def __init__(self, session_maker: Optional[AsyncSessionMaker] = None):
        from ..config.settings import settings
        self.session_maker = session_maker or AsyncSessionMaker
        self._clients: Dict[str, ZowPyClient] = {}
        self._lock = asyncio.Lock()
        self._shutdown = False
    
    def _raise_if_shutdown(self) -> None:
        if self._shutdown:
            raise RuntimeError("AccountManager já encerrado")
    
    async def add_account(self, account_id: str) -> ZowPyClient:
        """
        Adiciona conta de forma totalmente assíncrona.
        
        Args:
            account_id: ID da conta
        
        Returns:
            ZowPyClient: Cliente da conta
        
        Raises:
            RuntimeError: Se o manager já foi encerrado (shutdown)
        """
        self._raise_if_shutdown()
        async with self._lock:
            if account_id in self._clients:
                return self._clients[account_id]
            
            client = ZowPyClient(account_id, self.session_maker)
            self._clients[account_id] = client
            
            logger.info(f"Conta {account_id} adicionada")
            return client
    
    async def remove_account(self, account_id: str) -> None:
        """
        Remove conta de forma totalmente assíncrona.
        Desconecta completamente a conta e remove do manager.
        
        Args:
            account_id: ID da conta
        """
        self._raise_if_shutdown()
        async with self._lock:
            if account_id not in self._clients:
                return
            client = self._clients.pop(account_id)
        try:
            await client.disconnect()
        except Exception as e:
            logger.warning(f"Erro ao desconectar conta {account_id}: {e}")
        logger.info(f"Conta {account_id} removida")
    
    async def get_account(self, account_id: str) -> Optional[ZowPyClient]:
        """
        Obtém conta de forma assíncrona.
        
        Args:
            account_id: ID da conta
        
        Returns:
            ZowPyClient ou None
        
        Raises:
            RuntimeError: Se o manager já foi encerrado (shutdown)
        """
        self._raise_if_shutdown()
        async with self._lock:
            return self._clients.get(account_id)
    
    async def connect_all(self) -> None:
        """Conecta todas contas de forma assíncrona"""
        self._raise_if_shutdown()
        tasks: list = []
        async with self._lock:
            for account_id, client in self._clients.items():
                tasks.append((account_id, client.connect()))
        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )
        for (account_id, _), res in zip(tasks, results):
            if isinstance(res, Exception):
                logger.warning(f"Erro ao conectar conta {account_id}: {res}")
    
    async def disconnect_all(self) -> None:
        """
        Desconecta todas as contas de forma assíncrona.
        Garante que cada cliente chame disconnect() e loga falhas por conta.
        """
        self._raise_if_shutdown()
        async with self._lock:
            items = [(aid, c) for aid, c in self._clients.items()]
        if not items:
            return
        results = await asyncio.gather(
            *[c.disconnect() for _, c in items],
            return_exceptions=True,
        )
        for (account_id, _), res in zip(items, results):
            if isinstance(res, Exception):
                logger.warning(f"Erro ao desconectar conta {account_id}: {res}")
    
    async def shutdown(self) -> None:
        """
        Encerra o manager completamente.
        Desconecta todas as contas, limpa referências e impede uso posterior.
        """
        if self._shutdown:
            return
        await self.disconnect_all()
        async with self._lock:
            self._clients.clear()
        self._shutdown = True
        logger.info("AccountManager encerrado")













