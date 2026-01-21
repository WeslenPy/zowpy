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
    
    async def add_account(self, account_id: str) -> ZowPyClient:
        """
        Adiciona conta de forma totalmente assíncrona.
        
        Args:
            account_id: ID da conta
        
        Returns:
            ZowPyClient: Cliente da conta
        """
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
        
        Args:
            account_id: ID da conta
        """
        async with self._lock:
            if account_id not in self._clients:
                return
            
            client = self._clients.pop(account_id)
            await client.disconnect()
            
            logger.info(f"Conta {account_id} removida")
    
    async def get_account(self, account_id: str) -> Optional[ZowPyClient]:
        """
        Obtém conta de forma assíncrona.
        
        Args:
            account_id: ID da conta
        
        Returns:
            ZowPyClient ou None
        """
        async with self._lock:
            return self._clients.get(account_id)
    
    async def connect_all(self) -> None:
        """Conecta todas contas de forma assíncrona"""
        tasks = []
        async with self._lock:
            for account_id, client in self._clients.items():
                tasks.append(client.connect())
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def disconnect_all(self) -> None:
        """Desconecta todas contas de forma assíncrona"""
        tasks = []
        async with self._lock:
            for account_id, client in self._clients.items():
                tasks.append(client.disconnect())
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def shutdown(self) -> None:
        """Encerra manager de forma assíncrona"""
        await self.disconnect_all()












