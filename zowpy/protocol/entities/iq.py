"""
IQ Protocol Entities - Entidades de IQ.

Baseado em IqProtocolEntity, GetKeysIqProtocolEntity, SetKeysIqProtocolEntity do zowsuplib.
"""

from typing import Optional, List, Dict, Any
from .base import ProtocolEntity


class IqProtocolEntity(ProtocolEntity):
    """
    Entidade de IQ <iq>.
    
    Baseado em IqProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        xmlns: str,
        iq_type: str = "get",
        iq_id: Optional[str] = None,
        to: Optional[str] = None,
        from_jid: Optional[str] = None,
        children: Optional[List[ProtocolEntity]] = None
    ):
        """
        Cria entidade de IQ.
        
        Args:
            xmlns: XMLNS do IQ (ex: "w:g2", "usync")
            iq_type: Tipo do IQ (get, set, result, error)
            iq_id: ID do IQ (gerado se None)
            to: JID de destino (opcional)
            from_jid: JID de origem (opcional)
            children: Filhos do node
        """
        if not iq_id:
            iq_id = self._generate_id(short=True)
        
        attributes = {
            "id": iq_id,
            "type": iq_type,
            "xmlns": xmlns
        }
        
        if to:
            attributes["to"] = to
        
        if from_jid:
            attributes["from"] = from_jid
        
        super().__init__(
            tag="iq",
            attributes=attributes,
            children=children or []
        )
        
        self.iq_id = iq_id
        self.iq_type = iq_type
        self.xmlns = xmlns


class GetKeysIqProtocolEntity(IqProtocolEntity):
    """
    Entidade de IQ para obter chaves <iq type="get" xmlns="encrypt">.
    
    Baseado em GetKeysIqProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        jids: List[str],
        iq_id: Optional[str] = None,
        to: Optional[str] = None
    ):
        """
        Cria IQ para obter chaves.
        
        Args:
            jids: Lista de JIDs para obter chaves
            iq_id: ID do IQ (gerado se None)
            to: JID de destino (opcional)
        """
        children = []
        
        for jid in jids:
            key_node = ProtocolEntity(
                tag="key",
                attributes={"jid": jid}
            )
            children.append(key_node)
        
        super().__init__(
            xmlns="encrypt",
            iq_type="get",
            iq_id=iq_id,
            to=to,
            children=children
        )
        
        self.jids = jids


class SetKeysIqProtocolEntity(IqProtocolEntity):
    """
    Entidade de IQ para definir chaves <iq type="set" xmlns="encrypt">.
    
    Baseado em SetKeysIqProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        identity_key: bytes,
        signed_pre_key: bytes,
        pre_keys: List[Dict[str, Any]],
        registration_id: int,
        iq_id: Optional[str] = None,
        to: Optional[str] = None
    ):
        """
        Cria IQ para definir chaves.
        
        Args:
            identity_key: Chave de identidade (bytes)
            signed_pre_key: Signed pre-key (bytes)
            pre_keys: Lista de pre-keys [{"id": int, "key": bytes}, ...]
            registration_id: ID de registro
            iq_id: ID do IQ (gerado se None)
            to: JID de destino (opcional)
        """
        children = []
        
        # Node <registration>
        reg_node = ProtocolEntity(
            tag="registration",
            data=str(registration_id).encode()
        )
        children.append(reg_node)
        
        # Node <type>
        type_node = ProtocolEntity(
            tag="type",
            data=b"5"  # Curve.DJB_TYPE
        )
        children.append(type_node)
        
        # Node <identity>
        identity_node = ProtocolEntity(
            tag="identity",
            data=identity_key
        )
        children.append(identity_node)
        
        # Node <signed>
        signed_node = ProtocolEntity(
            tag="signed",
            data=signed_pre_key
        )
        children.append(signed_node)
        
        # Nodes <key> para cada pre-key
        for pre_key in pre_keys:
            key_node = ProtocolEntity(
                tag="key",
                attributes={"id": str(pre_key["id"])},
                data=pre_key["key"]
            )
            children.append(key_node)
        
        super().__init__(
            xmlns="encrypt",
            iq_type="set",
            iq_id=iq_id,
            to=to,
            children=children
        )
        
        self.identity_key = identity_key
        self.signed_pre_key = signed_pre_key
        self.pre_keys = pre_keys
        self.registration_id = registration_id

