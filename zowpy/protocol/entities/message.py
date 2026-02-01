"""
Message Protocol Entities - Entidades de mensagem.

Baseado em MessageProtocolEntity do zowsuplib.
"""

import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from zowpy.protocol.entities.attributes.attributes_message import MessageAttributes
from .base import ProtocolEntity
from .enc import EncProtocolEntity
from .attributes.attributes_message_meta import MessageMetaAttributes
from loguru import logger

class MessageProtocolEntity(ProtocolEntity):
    """
    Entidade de mensagem <message>.
    
    Baseado em MessageProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        to: str,
        message_type: str = "text",
        message_id: Optional[str] = None,
        from_jid: Optional[str] = None,
        timestamp: Optional[int] = None,
        participant: Optional[str] = None,
        children: Optional[List[ProtocolEntity]] = None
    ):
        """
        Cria entidade de mensagem.
        
        Args:
            to: JID do destinatário
            message_type: Tipo da mensagem (text, image, audio, etc.)
            message_id: ID da mensagem (gerado se None)
            from_jid: JID do remetente (opcional)
            timestamp: Timestamp (gerado se None)
            participant: JID do participante (opcional, para grupos)
            children: Filhos do node (enc, proto, etc.)
        """
        if not message_id:
            message_id = self._generate_id()
        
        timestamp = timestamp
        
        attributes = {
            "to": to,
            "type": message_type,
            "id": message_id,
        }


        logger.debug(f"Timestamp: {timestamp}")

        # if timestamp:
        #     attributes["t"] = str(timestamp)
        
        if from_jid:
            attributes["from"] = from_jid
            
        if participant:
            attributes["participant"] = participant
        
        super().__init__(
            tag="message",
            attributes=attributes,
            children=children or []
        )
        
        self.message_id = message_id
        self.to = to
        self.message_type = message_type
        self.participant = participant


class ProtomessageProtocolEntity(MessageProtocolEntity):
    """
    Entidade base para mensagens que contêm um nó <proto>.
    
    Gerencia a conversão de MessageAttributes para bytes Protobuf e a inclusão
    do nó <proto> no nó <message> final.
    """
    
    def __init__(
        self,
        message_attributes: Any,  # MessageAttributes
        message_meta_attributes: MessageMetaAttributes,
        message_type:str="text",
        message_id:Optional[str] = None,
    ):
        """
        Inicializa ProtomessageProtocolEntity.
        
        Args:
            message_attributes: Atributos de conteúdo da mensagem
            message_meta_attributes: Metadados da mensagem (id, to, t, etc.)
        """
        # Inicializa MessageProtocolEntity com os metadados
        super().__init__(
            message_type=message_type,
            to=message_meta_attributes.recipient,
            message_id=message_id or message_meta_attributes.id,
            participant=message_meta_attributes.participant
        )
        
        self._message_attributes = message_attributes
        self._message_meta_attributes = message_meta_attributes
        
        # Atualiza atributos extras do nó <message> a partir do meta
        self.attributes.update(message_meta_attributes.to_dict())

    def to_protocol_node(self) -> 'ProtocolNode':
        """
        Converte para ProtocolNode, adicionando o nó <proto>.
        
        Returns:
            ProtocolNode da mensagem completo com <proto>
        """
        # Obtém o nó <message> básico
        node = super().to_protocol_node()
        
        # Converte atributos para bytes Protobuf
        from .attributes.converter import AttributesConverter
        converter = AttributesConverter.get()
        proto_bytes = converter.message_to_protobytes(self._message_attributes)
        
        # Cria nó <proto>
        from ..structs import ProtocolNode
        proto_node = ProtocolNode(
            tag="proto",
            data=proto_bytes
        )
        
        # Adiciona <proto> como filho de <message>
        node.children.append(proto_node)
        
        return node


class TextMessageProtocolEntity(MessageProtocolEntity):
    """
    Entidade de mensagem de texto.
    
    Simplifica criação de mensagens de texto com criptografia.
    """
    
    def __init__(
        self,
        to: str,
        text: str,
        enc_node: Optional[EncProtocolEntity] = None,
        proto_data: Optional[bytes] = None,
        message_id: Optional[str] = None,
        from_jid: Optional[str] = None,
        participant: Optional[str] = None
    ):
        """
        Cria mensagem de texto.
        
        Args:
            to: JID do destinatário
            text: Texto da mensagem
            enc_node: Node <enc> com dados criptografados
            proto_data: Dados protobuf (opcional, para node <proto>)
            message_id: ID da mensagem (gerado se None)
            from_jid: JID do remetente (opcional)
            participant: JID do participante (opcional, para grupos)
        """
        children = []
        
        if enc_node:
            children.append(enc_node)
        
        if proto_data:
            proto_node = ProtocolEntity(
                tag="proto",
                data=proto_data
            )
            children.append(proto_node)
        
        super().__init__(
            to=to,
            message_type="text",
            message_id=message_id,
            from_jid=from_jid,
            participant=participant,
            children=children
        )
        
        self.text = text


class ExtendedTextMessageProtocolEntity(ProtomessageProtocolEntity):
    """
    Entidade de mensagem de texto estendida.
    
    Suporta formatação, cores, fontes, previews de links, etc.
    Baseado em ExtendedTextMessage do protobuf e ExtendedTextMessageProtocolEntity do zowsuplib.
    """
    
    # Font types (do protobuf ExtendedTextMessage.FontType)
    FONT_SANS_SERIF = 0
    FONT_SERIF = 1
    FONT_NORICAN_REGULAR = 2
    FONT_BRYNDAN_WRITE = 3
    FONT_BEBASNEUE_REGULAR = 4
    FONT_OSWALD_HEAVY = 5
    
    # Preview types (do protobuf ExtendedTextMessage.PreviewType)
    PREVIEW_NONE = 0
    PREVIEW_VIDEO = 1
    
    def __init__(
        self,
        extended_text_attributes: Any,  # ExtendedTextAttributes
        meta_attributes: MessageMetaAttributes,
        message_id:Optional[str]=None,
    ):
        """
        Cria mensagem de texto estendida.
        
        Args:
            extended_text_attributes: Atributos de texto estendido
            meta_attributes: Metadados da mensagem
        """
        from .attributes.attributes_message import MessageAttributes
        
        # Cria MessageAttributes envolvendo os atributos de texto estendido
        message_attributes = MessageAttributes(
            extended_text=extended_text_attributes
        )
        
        # Inicializa via ProtomessageProtocolEntity
        super().__init__(
            message_attributes=message_attributes,
            message_meta_attributes=meta_attributes,
            message_id=message_id,
        )
        
        self.extended_text_attributes = extended_text_attributes
        self.meta_attributes = meta_attributes
    
    def to_protobuf(self):
        """
        Converte para protobuf ExtendedTextMessage.
        
        Returns:
            e2e_pb2.Message.ExtendedTextMessage
        """
        from .attributes.converter import AttributesConverter
        converter = AttributesConverter.get()
        return converter.extendedtext_to_proto(self.extended_text_attributes)




class ReactionMessageProtocolEntity(ProtomessageProtocolEntity):
    """
    <message from="5356260450362:0@lid" type="reaction" id="A51524CC65529C0E4D017C88F04D9471" verified_level="unknown" notify="Hyper Duck" verified_name="4497206798683073789" sender_pn="559885700260@s.whatsapp.net" t="1769960454">
        <enc v="2" type="msg" decrypt-fail="hide">
            0x330a210597fceebf3c6d223f0b8601e71897d740ee2f8bd05501fb46ee8621e466d6280d10031800226081e13a2314c04a987335ba5f8a525fa53c1bb1fa3ae208a3836c2311d40153b142c719c4a0bb0b2eb4cef785905ca1a21a5d95e235c14d62429d1ac5f7f181b16f8a1e1f541931d33c978f25a52eb71155fea1d870d7f7678a812073ae944ff171d0cf8311b52db5
        </enc>
    </message>
    """
    def __init__(self,reaction_attr,message_meta_attributes=None, to=None):
        

        super(ReactionMessageProtocolEntity, self).__init__(message_type="reaction",
                                                            message_attributes= MessageAttributes(reaction = reaction_attr), 
                                                            message_meta_attributes=message_meta_attributes)




    

