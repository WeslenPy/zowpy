"""
Presence Protocol Entity - Entidade de presence.

Baseado em PresenceProtocolEntity do zowsuplib.
"""

from typing import Optional
from .base import ProtocolEntity


class PresenceProtocolEntity(ProtocolEntity):
    """
    Entidade de presence <presence>.
    
    Baseado em PresenceProtocolEntity do zowsuplib.
    """
    
    TYPE_AVAILABLE = "available"
    TYPE_UNAVAILABLE = "unavailable"
    
    def __init__(
        self,
        presence_type: str = TYPE_AVAILABLE,
        to: Optional[str] = None,
        from_jid: Optional[str] = None
    ):
        """
        Cria entidade de presence.
        
        Args:
            presence_type: Tipo de presence (available, unavailable, composing, paused)
            to: JID de destino (opcional)
            from_jid: JID de origem (opcional)
        """
        attributes = {}
        
        if presence_type:
            attributes["type"] = presence_type
        
        if to:
            attributes["to"] = to
        
        if from_jid:
            attributes["from"] = from_jid
        
        super().__init__(
            tag="presence",
            attributes=attributes
        )
        
        self.presence_type = presence_type

