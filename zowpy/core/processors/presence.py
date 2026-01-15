"""
Presence Processor - Processa presence recebidos.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter


class PresenceProcessor(BaseProcessor):
    """Processa presence recebidos"""
    
    def __init__(self, events: AsyncEventEmitter):
        """
        Inicializa processor.
        
        Args:
            events: Event emitter para emitir eventos
        """
        self._events = events
    
    def get_priority(self) -> int:
        """Presence têm prioridade baixa"""
        return 1
    
    async def can_handle(self, node: ProtocolNode) -> bool:
        """Verifica se é um presence"""
        return node.tag == "presence"
    
    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa presence.
        
        Args:
            node: Protocol node do presence
            raw_data: Dados brutos (não usado)
        
        Returns:
            Dict com dados processados do presence
        """
        from_jid = node.get_attribute("from")
        presence_type = node.get_attribute("type")
        
        logger.debug(f"Processando presence: type={presence_type}, from={from_jid}")
        
        presence_data: Dict[str, Any] = {
            "type": presence_type,
            "from": from_jid,
        }
        
        # Emite evento
        await self._events.emit("presence", presence_data)
        
        return presence_data

