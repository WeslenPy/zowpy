"""
DownloadableMediaMessageProtocolEntity - Entidade base para mídia downloadable.

Baseado em zowsuplib/yowsup/layers/protocol_media/protocolentities/message_media_downloadable.py
"""

from typing import Optional
from loguru import logger

from .message_media import MediaMessageProtocolEntity
from ..attributes import MessageAttributes, MessageMetaAttributes, DownloadableMediaMessageAttributes


class DownloadableMediaMessageProtocolEntity(MediaMessageProtocolEntity):
    """
    Entidade base para mensagens de mídia que podem ser baixadas.
    
    Herda de MediaMessageProtocolEntity e adiciona propriedades comuns de mídia downloadable.
    """
    
    def __init__(
        self,
        media_type: str,
        message_attrs: MessageAttributes,
        message_meta_attrs: MessageMetaAttributes
    ):
        """
        Inicializa DownloadableMediaMessageProtocolEntity.
        
        Args:
            media_type: Tipo de mídia (image, video, audio, document, sticker)
            message_attrs: Atributos da mensagem
            message_meta_attrs: Metadados da mensagem
        """
        super(DownloadableMediaMessageProtocolEntity, self).__init__(
            media_type, message_attrs, message_meta_attrs
        )
    
    @property
    def downloadablemedia_specific_attributes(self) -> DownloadableMediaMessageAttributes:
        """
        Retorna atributos específicos de mídia downloadable.
        
        Deve ser implementado pelas subclasses.
        """
        raise NotImplementedError()
    
    @property
    def url(self) -> Optional[str]:
        """URL da mídia no servidor WhatsApp."""
        return self.downloadablemedia_specific_attributes.url
    
    @url.setter
    def url(self, value: Optional[str]):
        """Define URL da mídia."""
        self.downloadablemedia_specific_attributes.url = value
    
    @property
    def mimetype(self) -> Optional[str]:
        """Tipo MIME da mídia."""
        return self.downloadablemedia_specific_attributes.mimetype
    
    @mimetype.setter
    def mimetype(self, value: Optional[str]):
        """Define tipo MIME."""
        self.downloadablemedia_specific_attributes.mimetype = value
    
    @property
    def file_sha256(self) -> bytes:
        """Hash SHA256 do arquivo original (32 bytes)."""
        return self.downloadablemedia_specific_attributes.file_sha256
    
    @file_sha256.setter
    def file_sha256(self, value: bytes):
        """Define hash SHA256 do arquivo."""
        self.downloadablemedia_specific_attributes.file_sha256 = value
    
    @property
    def file_length(self) -> int:
        """Tamanho do arquivo em bytes."""
        return self.downloadablemedia_specific_attributes.file_length
    
    @file_length.setter
    def file_length(self, value: int):
        """Define tamanho do arquivo."""
        self.downloadablemedia_specific_attributes.file_length = value
    
    @property
    def media_key(self) -> Optional[bytes]:
        """Chave de mídia para criptografia (32 bytes)."""
        return self.downloadablemedia_specific_attributes.media_key
    
    @media_key.setter
    def media_key(self, value: Optional[bytes]):
        """Define chave de mídia."""
        self.downloadablemedia_specific_attributes.media_key = value

