from typing import Optional, List, Union
from .iq import IqProtocolEntity
from ...protocol.structs import ProtocolNode
from ...utils.constants import YowConstants

class TrustContactIqProtocolEntity(IqProtocolEntity):
    """
    Entidade de IQ para confiar em contatos <iq xmlns="privacy" type="set">.
    
    Baseado em TrustContactIqProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        jids: Union[str, List[str]],
        timestamp: int,
        iq_id: Optional[str] = None
    ):
        """
        Cria IQ para confiar em contatos.
        
        Args:
            jids: JIDs dos contatos (string separada por vírgula ou lista)
            timestamp: Timestamp Unix
            iq_id: ID do IQ (gerado se None)
        """
        super().__init__(
            xmlns="privacy",
            iq_type="set",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER
        )
        
        # Normaliza jids para string separada por vírgula
        if isinstance(jids, list):
            self.jids = ",".join(jids)
        else:
            self.jids = jids
        
        self.timestamp = timestamp
    
    def to_protocol_node(self) -> ProtocolNode:
        """
        Converte para ProtocolNode.
        
        Returns:
            ProtocolNode equivalente
        """
        node = super().to_protocol_node()
        
        # Cria node <tokens>
        tokens_node = ProtocolNode(tag="tokens", attributes={})
        
        # Adiciona um <token> para cada JID
        jid_list = self.jids.split(",")
        for jid in jid_list:
            jid = jid.strip()
            if not jid:
                continue
            
            token_node = ProtocolNode(
                tag="token",
                attributes={
                    "jid": jid,
                    "type": "trusted_contact",
                    "t": str(self.timestamp)
                }
            )
            tokens_node.children.append(token_node)
        
        node.children.append(tokens_node)
        
        return node
