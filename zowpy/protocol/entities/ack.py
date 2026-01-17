
from typing import Optional, List
from .base import ProtocolEntity



class AckProtocolEntity(ProtocolEntity):
    """
    Entidade de ack <ack>.
    
    Baseado em AckProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        message_id: str,
        ack_class: str = "message",
        to: Optional[str] = None,
        from_jid: Optional[str] = None
    ):
        """
        Cria entidade de ack.
        
        Args:
            message_id: ID da mensagem
            ack_class: Classe do ack (message, receipt, etc.)
            to: JID de destino (opcional)
            from_jid: JID de origem (opcional)
        """
        attributes = {
            "id": message_id,
            "class": ack_class
        }
        
        if to:
            attributes["to"] = to
        
        if from_jid:
            attributes["from"] = from_jid
        
        super().__init__(
            tag="ack",
            attributes=attributes
        )
        
        self.message_id = message_id
        self.ack_class = ack_class

