from typing import Optional
from .iq import IqProtocolEntity
from ...protocol.structs import ProtocolNode
from ...utils.constants import YowConstants

class PushIqProtocolEntity(IqProtocolEntity):
    """
    Entidade de IQ para obter configurações de push <iq xmlns="urn:xmpp:whatsapp:push" type="get">.
    
    Baseado em PushIqProtocolEntity do zowsuplib.
    """
    
    def __init__(self, iq_id: Optional[str] = None):
        """
        Cria IQ para push config.
        
        Args:
            iq_id: ID do IQ (gerado se None)
        """
        super().__init__(
            xmlns="urn:xmpp:whatsapp:push",
            iq_type="get",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER
        )
    
    def to_protocol_node(self) -> ProtocolNode:
        """
        Converte para ProtocolNode.
        
        Returns:
            ProtocolNode equivalente
        """
        node = super().to_protocol_node()
        
        # Cria node <config version="1"/>
        config_node = ProtocolNode(
            tag="config",
            attributes={"version": "1"}
        )
        
        node.children.append(config_node)
        
        return node
