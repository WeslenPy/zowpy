
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


class OutgoingAckProtocolEntity(AckProtocolEntity):
    """
    Entidade de ack de saída (outgoing).
    
    <ack type="{{delivery | read}}" class="{{message | receipt | ?}}" id="{{MESSAGE_ID}}" to="{{TO_JID}}">
    </ack>
    
    <ack to="{{GROUP_JID}}" participant="{{JID}}" id="{{MESSAGE_ID}}" class="receipt" type="{{read | }}">
    </ack>
    
    Baseado em OutgoingAckProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        message_id: str,
        ack_class: str = "message",
        ack_type: Optional[str] = None,
        to: Optional[str] = None,
        participant: Optional[str] = None
    ):
        """
        Cria entidade de ack de saída.
        
        Args:
            message_id: ID da mensagem
            ack_class: Classe do ack (message, receipt, etc.)
            ack_type: Tipo do ack (delivery, read, etc.)
            to: JID de destino
            participant: JID do participante (para grupos)
        """
        super().__init__(
            message_id=message_id,
            ack_class=ack_class,
            to=to
        )
        
        self.ack_type = ack_type
        self.participant = participant
        
        # Atualiza atributos
        if ack_type:
            self.attributes["type"] = ack_type
        
        if to:
            self.attributes["to"] = to
        
        if participant:
            self.attributes["participant"] = participant
    
    def to_protocol_node(self):
        """
        Converte entidade para ProtocolNode.
        
        Returns:
            ProtocolNode equivalente
        """
        return self
