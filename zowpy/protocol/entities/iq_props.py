from typing import Optional
from .iq import IqProtocolEntity
from ...protocol.structs import ProtocolNode
from ...utils.constants import YowConstants

class PropsIqProtocolEntity(IqProtocolEntity):
    """
    Entidade de IQ para obter propriedades <iq xmlns="w" type="get">.
    
    Baseado em PropsIqProtocolEntity do zowsuplib.
    """
    
    def __init__(self, iq_id: Optional[str] = None):
        """
        Cria IQ para props.
        
        Args:
            iq_id: ID do IQ (gerado se None)
        """
        super().__init__(
            xmlns="w",
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
        
        # Cria node <props protocol="2" hash=""/>
        props_node = ProtocolNode(
            tag="props",
            attributes={
                "protocol": "2",
                "hash": ""
            }
        )
        
        node.children.append(props_node)
        
        return node
