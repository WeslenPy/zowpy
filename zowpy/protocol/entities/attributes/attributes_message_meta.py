"""
MessageMetaAttributes - Metadados de mensagem.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_message_meta.py
"""

from typing import Any, Optional
from loguru import logger

class MessageMetaAttributes:
    """
    Atributos de metadados para mensagens.
    
    Contém informações sobre remetente, destinatário, timestamp, etc.
    """
    
    ID_ANDROID = 0
    ID_IOS = 1
    
    def __init__(
        self,
        id: Optional[str] = None,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        notify: Optional[str] = None,
        timestamp: Optional[int] = None,
        participant: Optional[str] = None,
        offline: Optional[bool] = None,
        retry: Optional[int] = None,
        fromMe: bool = False,
        category: Optional[str] = None,
        phash: Optional[str] = None,
        edit: Optional[str] = None,
        sender_pn: Optional[str] = None,
        from_pn: Optional[str] = None,
        from_lid: Optional[str] = None,
    ):
        """
        Inicializa MessageMetaAttributes.
        
        Args:
            id: ID da mensagem
            sender: JID do remetente
            recipient: JID do destinatário
            notify: Nome para notificação
            timestamp: Timestamp da mensagem
            participant: JID do participante (para grupos)
            offline: Se a mensagem foi enviada offline
            retry: Número de tentativas
            fromMe: Se a mensagem foi enviada por mim
            category: Categoria da mensagem
            phash: Hash do participante
            edit: ID da mensagem original se editada
            sender_pn: JID do remetente com número de telefone
            from_pn: JID de origem com número de telefone
        """
        self.id = id or self.ID_ANDROID
        self.sender = sender
        self.sender_pn = sender_pn
        self.from_pn = from_pn
        self.recipient = recipient
        self.notify = notify
        self.timestamp = int(timestamp) if timestamp else None
        self.participant = participant
        self.offline = offline in ("1", True)
        self.retry = int(retry) if retry else None
        self.fromMe = fromMe if fromMe else False
        self.category = category
        self.phash = phash
        self.edit = edit
        self.from_lid = from_lid
    def to_dict(self) -> dict:
        """Retorna atributos para o node <message>."""
        attrs = {}
        if self.id: attrs["id"] = self.id
        if self.sender: attrs["from"] = self.sender
        if self.recipient: attrs["to"] = self.recipient
        if self.timestamp: attrs["t"] = str(self.timestamp)
        if self.participant: attrs["participant"] = self.participant
        if self.notify: attrs["notify"] = self.notify
        if self.offline: attrs["offline"] = "1"
        if self.retry: attrs["retry"] = str(self.retry)
        if self.category: attrs["category"] = self.category
        if self.phash: attrs["phash"] = self.phash
        if self.edit: attrs["edit"] = self.edit
        if self.sender_pn: attrs["sender_pn"] = self.sender_pn
        if self.from_pn: attrs["from_pn"] = self.from_pn
        if self.from_lid: attrs["from"] = self.from_lid
        return attrs
    
    @staticmethod
    def from_message_protocoltreenode(node: 'ProtocolNode', proto: Optional[Any] = None) -> 'MessageMetaAttributes':
        """
        Cria MessageMetaAttributes a partir de um ProtocolNode de mensagem.
        
        Args:
            node: ProtocolNode da mensagem
            proto: Protobuf da mensagem (opcional)
        
        Returns:
            MessageMetaAttributes
        """
        from ...structs import ProtocolNode
        
        logger.info(f"[MessageMetaAttributes] from_message_protocoltreenode chamado - node: {node}")
        
        fromMe = False
        to = None
        if proto is not None:
            if hasattr(proto, 'HasField') and proto.HasField("device_sent_message"):
                fromMe = True
                to = proto.device_sent_message.destination_jid
        
        sender_pn = node.attributes.get("sender_pn") if hasattr(node, 'attributes') else None
        from_pn = node.attributes.get("from_pn") if hasattr(node, 'attributes') else None
        
        logger.info(f"sender_pn: {sender_pn}")
        logger.info(f"from_pn: {from_pn}")
        
        return MessageMetaAttributes(
            id=node.attributes.get("id"),
            sender=node.attributes.get("from"),
            from_lid=node.attributes.get("from"),
            recipient=node.attributes.get("to") if to is None else to,
            notify=node.attributes.get("notify"),
            timestamp=node.attributes.get("t"),
            participant=node.attributes.get("participant"),
            offline=node.attributes.get("offline"),
            retry=node.attributes.get("retry"),
            fromMe=fromMe,
            category=node.attributes.get("category"),
            phash=node.attributes.get("phash"),
            edit=node.attributes.get("edit"),
            sender_pn=sender_pn,
            from_pn=from_pn,
        )

