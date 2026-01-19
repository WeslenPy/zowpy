"""
DocumentDownloadableMediaMessageProtocolEntity - Entidade para mensagens de documento.

Baseado em zowsuplib/yowsup/layers/protocol_media/protocolentities/message_media_downloadable_document.py
"""

from typing import Optional

from .message_media_downloadable import DownloadableMediaMessageProtocolEntity
from ..attributes import DocumentAttributes, MessageMetaAttributes, MessageAttributes


class DocumentDownloadableMediaMessageProtocolEntity(DownloadableMediaMessageProtocolEntity):
    """
    Entidade para mensagens de documento.
    
    Herda de DownloadableMediaMessageProtocolEntity e adiciona propriedades específicas de documento.
    """
    
    def __init__(
        self,
        document_attrs: DocumentAttributes,
        message_meta_attrs: MessageMetaAttributes
    ):
        """
        Inicializa DocumentDownloadableMediaMessageProtocolEntity.
        
        Args:
            document_attrs: Atributos de documento
            message_meta_attrs: Metadados da mensagem
        """
        super(DocumentDownloadableMediaMessageProtocolEntity, self).__init__(
            "document", MessageAttributes(document=document_attrs), message_meta_attrs
        )
    
    @property
    def media_specific_attributes(self) -> DocumentAttributes:
        """Atributos específicos de documento."""
        return self.message_attributes.document
    
    @property
    def downloadablemedia_specific_attributes(self) -> Optional['DownloadableMediaMessageAttributes']:
        """Atributos de mídia downloadable."""
        if self.message_attributes.document:
            return self.message_attributes.document.downloadablemedia_attributes
        return None
    
    @property
    def file_name(self) -> str:
        """Nome do arquivo."""
        return self.media_specific_attributes.file_name
    
    @file_name.setter
    def file_name(self, value: str):
        """Define nome do arquivo."""
        self.media_specific_attributes.file_name = value
    
    @property
    def file_length(self) -> int:
        """Tamanho do arquivo em bytes."""
        return self.media_specific_attributes.file_length
    
    @file_length.setter
    def file_length(self, value: int):
        """Define tamanho do arquivo."""
        self.media_specific_attributes.file_length = value
    
    @property
    def title(self) -> Optional[str]:
        """Título do documento."""
        return self.media_specific_attributes.title
    
    @title.setter
    def title(self, value: Optional[str]):
        """Define título do documento."""
        self.media_specific_attributes.title = value
    
    @property
    def page_count(self) -> Optional[int]:
        """Número de páginas."""
        return self.media_specific_attributes.page_count
    
    @page_count.setter
    def page_count(self, value: Optional[int]):
        """Define número de páginas."""
        self.media_specific_attributes.page_count = value
    
    @property
    def jpeg_thumbnail(self) -> Optional[bytes]:
        """Thumbnail JPEG do documento."""
        return self.media_specific_attributes.jpeg_thumbnail
    
    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail JPEG."""
        self.media_specific_attributes.jpeg_thumbnail = value
    
    @property
    def caption(self) -> Optional[str]:
        """Legenda do documento."""
        return self.media_specific_attributes.caption
    
    @caption.setter
    def caption(self, value: Optional[str]):
        """Define legenda do documento."""
        self.media_specific_attributes.caption = value

