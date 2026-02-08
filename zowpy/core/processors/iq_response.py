"""
IQ Response Processor - Gerencia callbacks para respostas de IQ.

Sistema moderno para gerenciar respostas assíncronas de IQs.
"""

import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from loguru import logger

from ...protocol.structs import ProtocolNode


class IQCallback:
    """Callback para resposta de IQ"""
    
    def __init__(
        self,
        callback: Callable,
        timeout: float = 30.0,
        created_at: Optional[datetime] = None
    ):
        self.callback = callback
        self.timeout = timeout
        self.created_at = created_at or datetime.now()
        self.completed = False
    
    def is_expired(self) -> bool:
        """Verifica se callback expirou"""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.timeout


class IQResponseProcessor:
    """
    Processa respostas de IQ e chama callbacks registrados.
    
    Sistema baseado em registro de callbacks por IQ ID.
    """
    
    def __init__(self):
        """Inicializa processor"""
        self._callbacks: Dict[str, IQCallback] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def register_callback(
        self,
        iq_id: str,
        callback: Callable[[ProtocolNode], Any],
        timeout: float = 30.0
    ) -> None:
        """
        Registra callback para resposta de IQ.
        
        Args:
            iq_id: ID do IQ
            callback: Função async que recebe o node de resposta
            timeout: Timeout em segundos (padrão: 30s)
        """
        self._callbacks[iq_id] = IQCallback(callback, timeout)
        logger.debug(f"Callback registrado para IQ {iq_id} (timeout: {timeout}s)")
        
        # Inicia cleanup task se não estiver rodando
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_callbacks())
    
    def unregister_callback(self, iq_id: str) -> None:
        """
        Remove callback registrado.
        
        Args:
            iq_id: ID do IQ
        """
        if iq_id in self._callbacks:
            del self._callbacks[iq_id]
            logger.debug(f"Callback removido para IQ {iq_id}")
    
    def has_callback(self, iq_id: str) -> bool:
        """
        Verifica rapidamente se existe um callback registrado para o ID.
        
        Args:
            iq_id: ID do IQ
            
        Returns:
            True se existe callback, False caso contrário
        """
        if not iq_id:
            return False
        return iq_id in self._callbacks

    async def process_iq_response(self, node: ProtocolNode) -> bool:
        """
        Processa resposta de IQ e chama callback se registrado.
        
        Args:
            node: Protocol node da resposta IQ
        
        Returns:
            True se callback foi chamado, False caso contrário
        """
        iq_id = node.get_attribute("id")
        iq_type = node.get_attribute("type")
        
        if not iq_id:
            logger.debug("IQ response sem ID, ignorando")
            return False
        
        # Verifica se há callback registrado
        if iq_id not in self._callbacks:
            logger.debug(f"Nenhum callback registrado para IQ {iq_id}")
            return False
        
        callback_info = self._callbacks[iq_id]
        
        # Verifica se expirou
        if callback_info.is_expired():
            logger.warning(f"Callback para IQ {iq_id} expirou")
            self.unregister_callback(iq_id)
            return False
        
        # Chama callback
        try:
            logger.debug(f"Chamando callback para IQ {iq_id} (type: {iq_type})")
            if asyncio.iscoroutinefunction(callback_info.callback):
                await callback_info.callback(node)
            else:
                callback_info.callback(node)
            
            callback_info.completed = True
            self.unregister_callback(iq_id)
            return True
        
        except Exception as e:
            logger.error(f"Erro ao chamar callback para IQ {iq_id}: {e}", exc_info=True)
            self.unregister_callback(iq_id)
            return False
    
    async def _cleanup_expired_callbacks(self) -> None:
        """Remove callbacks expirados periodicamente"""
        while True:
            try:
                await asyncio.sleep(5.0)  # Verifica a cada 5 segundos
                
                expired_ids = [
                    iq_id for iq_id, callback in self._callbacks.items()
                    if callback.is_expired()
                ]
                
                for iq_id in expired_ids:
                    logger.debug(f"Removendo callback expirado para IQ {iq_id}")
                    self.unregister_callback(iq_id)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no cleanup de callbacks: {e}")
    
    def get_pending_count(self) -> int:
        """
        Retorna número de callbacks pendentes.
        
        Returns:
            Número de callbacks pendentes
        """
        return len(self._callbacks)
    
    def clear_all(self) -> None:
        """Remove todos os callbacks"""
        self._callbacks.clear()
        logger.debug("Todos os callbacks removidos")
    
    async def shutdown(self) -> None:
        """
        Finaliza o processor completamente.
        
        Cancela a cleanup task e limpa todos os callbacks.
        """
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Erro ao cancelar cleanup task: {e}")
        self._cleanup_task = None
        self.clear_all()
        logger.debug("IQResponseProcessor finalizado")

