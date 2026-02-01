"""
IB Processor - Processa nós <ib>.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...protocol.entities.ib import EdgeRoutingIbProtocolEntity
from .base import BaseProcessor


class IbProcessor(BaseProcessor):
    """
    Processa nós <ib>.
    
    Atualmente trata:
    - edge_routing: Atualização de informações de roteamento.
    """
    
    def __init__(self, event_emitter=None):
        """
        Inicializa processor.
        
        Args:
            event_emitter: EventEmitter para emitir eventos (opcional)
        """
        self._event_emitter = event_emitter

    async def can_handle(self, node: ProtocolNode) -> bool:
        """
        Verifica se pode processar o node.
        
        Args:
            node: Protocol node
        
        Returns:
            True se é nó <ib>
        """
        return node.tag == "ib"
    
    async def process(self, node: ProtocolNode, raw_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Processa nó <ib>.
        
        Args:
            node: Protocol node
            raw_data: Dados brutos
        
        Returns:
            Dict com informações processadas ou None
        """
        try:
            # Verifica se contém edge_routing
            if node.get_child("edge_routing"):
                entity = EdgeRoutingIbProtocolEntity.from_protocol_node(node)
                
                event_data = {
                    "routing_info": entity.routing_info,
                    "from": node.get_attribute("from")
                }
                
                logger.info(f"Recebido edge_routing de {event_data['from']}")
                await self._emit_event("ib:edge_routing", event_data)
                return event_data
            
            logger.debug(f"Nó <ib> recebido mas não contém edge_routing: {node}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao processar nó <ib>: {e}", exc_info=True)
            return None
    
    async def _emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Emite evento se event_emitter estiver disponível.
        """
        if self._event_emitter:
            try:
                await self._event_emitter.emit(event_name, data)
            except Exception as e:
                logger.error(f"Erro ao emitir evento {event_name}: {e}")
