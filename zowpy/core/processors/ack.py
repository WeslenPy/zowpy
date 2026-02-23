"""
Ack Processor - Processa acks recebidos.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter


class AckProcessor(BaseProcessor):
    """Processa acks recebidos"""
    
    def __init__(self, events: AsyncEventEmitter):
        """
        Inicializa processor.
        
        Args:
            events: Event emitter para emitir eventos
        """
        self._events = events
    
    def get_priority(self) -> int:
        """Acks têm prioridade média"""
        return 5
    
    async def can_handle(self, node: ProtocolNode) -> bool:
        """Verifica se é um ack"""
        return node.tag == "ack" 
    
    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa ack.
        
        Args:
            node: Protocol node do ack
            raw_data: Dados brutos (não usado)
        
        Returns:
            Dict com dados processados do ack
        """
        ack_id = node.get_attribute("id")
        ack_class = node.get_attribute("class")
        ack_type = node.get_attribute("type")
        from_jid = node.get_attribute("from")
        
        logger.debug(f"Processando ack: id={ack_id}, class={ack_class}, type={ack_type}, from={from_jid}")
        
        ack_data: Dict[str, Any] = {
            "id": ack_id,
            "class": ack_class,
            "type": ack_type,
            "from": from_jid,
        }
        
        # Emite evento
        await self._events.emit("ack", ack_data)
        
        return ack_data

