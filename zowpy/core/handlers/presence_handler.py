"""
Presence Handler - Gerencia operações de presença e status.

Handler público para presença e status do WhatsApp.
"""

from typing import Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from ..builders.presence_builder import PresenceBuilder


class PresenceHandler:
    """
    Gerencia operações de presença e status.
    
    Métodos públicos para definir presença e status.
    """
    
    def __init__(self, send_presence_fn: callable):
        """
        Inicializa handler.
        
        Args:
            send_presence_fn: Função async para enviar presence (recebe ProtocolNode)
        """
        self._send_presence = send_presence_fn
    
    async def set_presence(
        self,
        presence_type: str = PresenceBuilder.TYPE_AVAILABLE,
        to: Optional[str] = None
    ) -> bool:
        """
        Define presença.
        
        Args:
            presence_type: Tipo de presença (available, unavailable, composing, paused, recording)
            to: JID de destino (opcional, para presença direcionada)
        
        Returns:
            True se sucesso
        """
        logger.info(f"Definindo presença: type={presence_type}, to={to}")
        
        presence_node = PresenceBuilder.build_presence(
            to=to,
            presence_type=presence_type
        )
        
        try:
            await self._send_presence(presence_node)
            logger.info("Presença definida com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao definir presença: {e}")
            raise
    
    async def set_status(self, status: str) -> bool:
        """
        Define status.
        
        Args:
            status: Texto do status
        
        Returns:
            True se sucesso
        """
        logger.info(f"Definindo status: {status[:50]}")
        
        status_node = PresenceBuilder.build_status(status)
        
        try:
            await self._send_presence(status_node)
            logger.info("Status definido com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao definir status: {e}")
            raise

