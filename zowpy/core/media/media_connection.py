"""
Media Connection - Gerencia conexões de mídia com cache de TTL.

Baseado no comportamento do zowsuplib para obter e cachear media connection.
"""

import asyncio
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from loguru import logger


@dataclass
class MediaConnectionInfo:
    """Informações de conexão de mídia."""
    hosts: List[str]
    auth: str
    ttl: int  # Time to live em segundos
    timestamp: float  # Quando foi obtido
    
    @property
    def is_expired(self) -> bool:
        """Verifica se conexão expirou."""
        return time.time() - self.timestamp > self.ttl
    
    @property
    def age(self) -> float:
        """Idade da conexão em segundos."""
        return time.time() - self.timestamp


class MediaConnection:
    """
    Gerencia conexões de mídia com cache de TTL.
    
    Baseado no comportamento do zowsuplib:
    - Obtém media connection via IQ media_conn
    - Cacheia com TTL (padrão 24h)
    - Renova automaticamente quando expira
    """
    
    def __init__(self, ttl_buffer: float = 3600.0):
        """
        Inicializa gerenciador de media connection.
        
        Args:
            ttl_buffer: Buffer em segundos para renovar antes de expirar (padrão: 1h)
        """
        self._connection_info: Optional[MediaConnectionInfo] = None
        self._lock = asyncio.Lock()
        self._ttl_buffer = ttl_buffer
        
        # Callback para obter media connection via IQ
        self._get_media_conn_fn: Optional[callable] = None
    
    def set_get_media_conn_fn(self, fn: callable) -> None:
        """
        Define função para obter media connection via IQ.
        
        Args:
            fn: Função async que retorna MediaConnectionInfo
        """
        self._get_media_conn_fn = fn
    
    async def get_connection(self) -> Dict[str, Any]:
        """
        Obtém media connection (com cache).
        
        Retorna conexão cached se ainda válida, senão obtém nova.
        
        Returns:
            dict: {"hosts": [...], "auth": "...", "ttl": 86400}
        """
        async with self._lock:
            # Verifica se tem conexão cached e ainda válida
            if self._connection_info and not self._connection_info.is_expired:
                logger.debug(
                    f"Usando media connection cached "
                    f"(age: {self._connection_info.age:.1f}s, ttl: {self._connection_info.ttl}s)"
                )
                return {
                    "hosts": self._connection_info.hosts,
                    "auth": self._connection_info.auth,
                    "ttl": self._connection_info.ttl
                }
            
            # Renova se expirado ou se está próximo de expirar
            if self._connection_info and self._connection_info.age > (self._connection_info.ttl - self._ttl_buffer):
                logger.debug(
                    f"Media connection próximo de expirar "
                    f"(age: {self._connection_info.age:.1f}s, ttl: {self._connection_info.ttl}s), renovando"
                )
            
            # Obtém nova conexão
            if not self._get_media_conn_fn:
                raise RuntimeError("_get_media_conn_fn não configurada")
            
            logger.debug("Obtendo nova media connection via IQ...")
            connection_info = await self._get_media_conn_fn()
            
            if connection_info:
                self._connection_info = connection_info
                logger.info(
                    f"Media connection obtida: hosts={len(connection_info.hosts)}, "
                    f"ttl={connection_info.ttl}s"
                )
                
                return {
                    "hosts": connection_info.hosts,
                    "auth": connection_info.auth,
                    "ttl": connection_info.ttl
                }
            else:
                raise RuntimeError("Falha ao obter media connection")
    
    def update_from_iq_result(self, hosts: List[str], auth: str, ttl: int) -> None:
        """
        Atualiza conexão a partir de resposta IQ.
        
        Args:
            hosts: Lista de hosts
            auth: Token de autenticação
            ttl: Time to live em segundos
        """
        self._connection_info = MediaConnectionInfo(
            hosts=hosts,
            auth=auth,
            ttl=ttl,
            timestamp=time.time()
        )
        logger.debug(f"Media connection atualizada: hosts={len(hosts)}, ttl={ttl}s")
    
    def clear_cache(self) -> None:
        """Limpa cache de conexão."""
        async def _clear():
            async with self._lock:
                self._connection_info = None
                logger.debug("Media connection cache limpo")
        
        # Executa de forma síncrona se possível
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Se loop está rodando, cria task
            asyncio.create_task(_clear())
        else:
            loop.run_until_complete(_clear())
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do cache."""
        if self._connection_info:
            return {
                "cached": True,
                "age": self._connection_info.age,
                "ttl": self._connection_info.ttl,
                "expired": self._connection_info.is_expired,
                "hosts_count": len(self._connection_info.hosts)
            }
        else:
            return {
                "cached": False,
                "age": None,
                "ttl": None,
                "expired": None,
                "hosts_count": 0
            }

