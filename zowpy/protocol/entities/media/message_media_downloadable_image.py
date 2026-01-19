"""
ImageDownloadableMediaMessageProtocolEntity - Entidade para mensagens de imagem.

Baseado em zowsuplib/yowsup/layers/protocol_media/protocolentities/message_media_downloadable_image.py
"""

from typing import Optional, TYPE_CHECKING

from .message_media_downloadable import DownloadableMediaMessageProtocolEntity
from ..attributes import ImageAttributes, MessageMetaAttributes, MessageAttributes

if TYPE_CHECKING:
    from ..attributes import DownloadableMediaMessageAttributes


class ImageDownloadableMediaMessageProtocolEntity(DownloadableMediaMessageProtocolEntity):
    """
    Entidade para mensagens de imagem.
    
    Herda de DownloadableMediaMessageProtocolEntity e adiciona propriedades específicas de imagem.
    """
    
    def __init__(
        self,
        image_attrs: ImageAttributes,
        message_meta_attrs: MessageMetaAttributes
    ):
        """
        Inicializa ImageDownloadableMediaMessageProtocolEntity.
        
        Args:
            image_attrs: Atributos de imagem
            message_meta_attrs: Metadados da mensagem
        """
        super(ImageDownloadableMediaMessageProtocolEntity, self).__init__(
            "image", MessageAttributes(image=image_attrs), message_meta_attrs
        )
    
    @property
    def media_specific_attributes(self) -> ImageAttributes:
        """Atributos específicos de imagem."""
        return self.message_attributes.image
    
    @property
    def downloadablemedia_specific_attributes(self) -> 'DownloadableMediaMessageAttributes':
        """Atributos de mídia downloadable."""
        return self.message_attributes.image.downloadablemedia_attributes
    
    @property
    def width(self) -> int:
        """Largura da imagem em pixels."""
        return self.media_specific_attributes.width
    
    @width.setter
    def width(self, value: int):
        """Define largura da imagem."""
        self.media_specific_attributes.width = value
    
    @property
    def height(self) -> int:
        """Altura da imagem em pixels."""
        return self.media_specific_attributes.height
    
    @height.setter
    def height(self, value: int):
        """Define altura da imagem."""
        self.media_specific_attributes.height = value
    
    @property
    def jpeg_thumbnail(self) -> Optional[bytes]:
        """Thumbnail JPEG da imagem."""
        return self.media_specific_attributes.jpeg_thumbnail
    
    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail JPEG."""
        self.media_specific_attributes.jpeg_thumbnail = value if value is not None else b""
    
    @property
    def caption(self) -> Optional[str]:
        """Legenda da imagem."""
        return self.media_specific_attributes.caption
    
    @caption.setter
    def caption(self, value: Optional[str]):
        """Define legenda da imagem."""
        self.media_specific_attributes.caption = value if value is not None else ""

