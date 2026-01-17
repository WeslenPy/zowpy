"""
Async IQ Handler - Handler de IQ totalmente assíncrono.

Processa IQs de forma assíncrona.
"""

import asyncio
from typing import Dict, Callable, Optional
from loguru import logger

from ..core.events import AsyncEventEmitter


class AsyncIQHandler:
    """
    Handler de IQ totalmente assíncrono.
    Processa IQs de forma assíncrona.
    """
    
    def __init__(self, events: AsyncEventEmitter):
        self.events = events
        self._callbacks: Dict[str, Callable] = {}
        self._callbacks_lock = asyncio.Lock()
    
    async def handle_iq(self, iq_data: bytes) -> None:
        """
        Processa IQ de forma totalmente assíncrona.
        
        Args:
            iq_data: Dados do IQ
        """
        # Deserializa IQ
        iq = await asyncio.to_thread(self._deserialize_iq, iq_data)
        
        # Verifica se há callback registrado
        iq_id = iq.get("id")
        if iq_id:
            async with self._callbacks_lock:
                callback = self._callbacks.pop(iq_id, None)
            
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(iq)
                else:
                    await asyncio.to_thread(callback, iq)
        
        # Emite evento
        await self.events.emit("iq", iq)
    
    async def register_callback(self, iq_id: str, callback: Callable) -> None:
        """
        Registra callback para IQ de forma assíncrona.
        
        Args:
            iq_id: ID do IQ
            callback: Callback para chamar
        """
        async with self._callbacks_lock:
            self._callbacks[iq_id] = callback
    
    def _deserialize_iq(self, data: bytes) -> dict:
        """Deserializa IQ (pode ser síncrono)"""
        # Implementação específica
        return {"data": data}





