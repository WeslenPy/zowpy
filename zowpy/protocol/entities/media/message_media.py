"""
MediaMessageProtocolEntity - Entidade base para mensagens de mídia.

Baseado em zowsuplib/yowsup/layers/protocol_media/protocolentities/message_media.py
"""

from typing import Optional
from loguru import logger

from ..message import MessageProtocolEntity
from ..attributes import MessageAttributes, MessageMetaAttributes
from ....protocol.structs import ProtocolNode


class MediaMessageProtocolEntity(MessageProtocolEntity):
    """
    Entidade base para mensagens de mídia.
    
    Herda de MessageProtocolEntity e adiciona suporte para protobuf de mídia.
    """
    
    TYPE_MEDIA_IMAGE = "image"
    TYPE_MEDIA_VIDEO = "video"
    TYPE_MEDIA_AUDIO = "audio"
    TYPE_MEDIA_CONTACT = "contact"
    TYPE_MEDIA_LOCATION = "location"
    TYPE_MEDIA_DOCUMENT = "document"
    TYPE_MEDIA_GIF = "gif"
    TYPE_MEDIA_PTT = "ptt"
    TYPE_MEDIA_URL = "url"
    TYPE_MEDIA_STICKER = "sticker"
    TYPE_MEDIA_BUTTONS_RESPONSE = "buttons_response"
    TYPE_MEDIA_LIST = "list"
    TYPE_MEDIA_LIST_RESPONSE = "list_response"
    TYPE_PRODUCT = "product"
    TYPE_MEDIA_STICKER_1P = "1p_sticker"
    TYPE_MEDIA_AVATAR_STICKER = "avatar_sticker"
    
    TYPES_MEDIA = (
        TYPE_MEDIA_IMAGE, TYPE_MEDIA_AUDIO, TYPE_MEDIA_VIDEO,
        TYPE_MEDIA_CONTACT, TYPE_MEDIA_LOCATION, TYPE_MEDIA_DOCUMENT,
        TYPE_MEDIA_GIF, TYPE_MEDIA_PTT, TYPE_MEDIA_URL, TYPE_MEDIA_STICKER,
        TYPE_MEDIA_BUTTONS_RESPONSE, TYPE_MEDIA_LIST, TYPE_MEDIA_LIST_RESPONSE,
        TYPE_PRODUCT, TYPE_MEDIA_STICKER, TYPE_MEDIA_AVATAR_STICKER, TYPE_MEDIA_STICKER_1P
    )
    
    def __init__(
        self,
        media_type: str,
        message_attrs: MessageAttributes,
        message_meta_attrs: MessageMetaAttributes
    ):
        """
        Inicializa MediaMessageProtocolEntity.
        
        Args:
            media_type: Tipo de mídia (image, video, audio, etc.)
            message_attrs: Atributos da mensagem
            message_meta_attrs: Metadados da mensagem
        """
        # Cria MessageProtocolEntity com tipo "media"
        to = message_meta_attrs.recipient or ""
        message_id = message_meta_attrs.id
        from_jid = message_meta_attrs.sender
        timestamp = message_meta_attrs.timestamp
        
        super().__init__(
            to=to,
            message_type="media",
            message_id=message_id,
            from_jid=from_jid,
            timestamp=timestamp
        )
        
        self._media_type = media_type
        self._message_attributes = message_attrs
        self._message_meta_attributes = message_meta_attrs


    
    @property
    def message_secret(self) -> Optional[bytes]:
        """Chave de segredo da mensagem."""
        return self._message_attributes.message_secret
    
    @message_secret.setter
    def message_secret(self, message_secret: Optional[bytes]):
        """Define chave de segredo da mensagem."""
        self._message_attributes.message_secret = message_secret
    
    def __str__(self):
        out = super(MediaMessageProtocolEntity, self).__str__()
        return f"{out}\nmediatype={self.media_type}"
    
    @property
    def media_type(self) -> str:
        """Tipo de mídia."""
        return self._media_type
    
    @media_type.setter
    def media_type(self, value: str):
        """Define tipo de mídia."""
        if value not in MediaMessageProtocolEntity.TYPES_MEDIA:
            logger.warning(f"media type: '{value}' is not supported")
        self._media_type = value
    
    @property
    def message_attributes(self) -> MessageAttributes:
        """Atributos da mensagem."""
        return self._message_attributes
    
    @message_attributes.setter
    def message_attributes(self, value: MessageAttributes):
        """Define atributos da mensagem."""
        self._message_attributes = value
    
    @property
    def message_meta_attributes(self) -> MessageMetaAttributes:
        """Metadados da mensagem."""
        return self._message_meta_attributes
    
    @message_meta_attributes.setter
    def message_meta_attributes(self, value: MessageMetaAttributes):
        """Define metadados da mensagem."""
        self._message_meta_attributes = value
    
    def to_protocol_node(self):
        """
        Converte para ProtocolNode com node <proto> contendo dados protobuf.
        
        Usa o AttributesConverter para converter MessageAttributes em protobuf.
        """
        from ..attributes import AttributesConverter
        
        # Converte MessageAttributes para protobuf
        converter = AttributesConverter.get()
        proto_bytes = converter.message_to_protobytes(self.message_attributes)
        
        # Cria node <proto> com mediatype
        proto_node = ProtocolNode(
            tag="proto",
            attributes={"mediatype": self.media_type},
            data=proto_bytes
        )
        
        # Cria node <message> com children incluindo proto
        node = super().to_protocol_node()
        node.children = [proto_node]
        
        return node

