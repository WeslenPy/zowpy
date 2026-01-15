"""
Presence Builder - Constrói nodes para presença e status.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

from typing import Optional
from loguru import logger

from ...protocol.structs import ProtocolNode


class PresenceBuilder:
    """
    Constrói nodes para presença e status.
    
    Baseado nos protocol entities do zowsuplib:
    - PresenceProtocolEntity
    """
    
    # Tipos de presença
    TYPE_AVAILABLE = "available"
    TYPE_UNAVAILABLE = "unavailable"
    TYPE_COMPOSING = "composing"
    TYPE_PAUSED = "paused"
    TYPE_RECORDING = "recording"
    
    @staticmethod
    def build_presence(
        to: Optional[str] = None,
        presence_type: str = TYPE_AVAILABLE,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói node de presença.
        
        Args:
            to: JID de destino (opcional, para presença direcionada)
            presence_type: Tipo de presença (available, unavailable, composing, paused, recording)
            iq_id: ID do IQ (gerado se None, mas presença geralmente não usa IQ)
        
        Returns:
            ProtocolNode: Node de presença
        """
        attributes = {
            "type": presence_type
        }
        
        if to:
            attributes["to"] = to
        
        node = ProtocolNode(
            tag="presence",
            attributes=attributes,
            children=[]
        )
        
        logger.debug(f"Presence node construído: type={presence_type}, to={to}")
        return node
    
    @staticmethod
    def build_status(status: str) -> ProtocolNode:
        """
        Constrói node de status (via presence).
        
        Args:
            status: Texto do status
        
        Returns:
            ProtocolNode: Node de presença com status
        """
        node = PresenceBuilder.build_presence(presence_type=PresenceBuilder.TYPE_AVAILABLE)
        
        # Adiciona node <status> com texto
        status_data = status.encode("utf-8") if isinstance(status, str) else status
        status_node = ProtocolNode(
            tag="status",
            attributes={},
            data=status_data
        )
        
        node.children.append(status_node)
        logger.debug(f"Status node construído: {status[:50]}")
        return node

