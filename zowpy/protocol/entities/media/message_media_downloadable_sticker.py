"""
StickerDownloadableMediaMessageProtocolEntity - Entidade para mensagens de sticker.

Baseado em zowsuplib/yowsup/layers/protocol_media/protocolentities/message_media_downloadable_sticker.py
"""

from typing import Optional, TYPE_CHECKING

from .message_media_downloadable import DownloadableMediaMessageProtocolEntity
from ..attributes import StickerAttributes, MessageMetaAttributes, MessageAttributes

if TYPE_CHECKING:
    from ..attributes import DownloadableMediaMessageAttributes


class StickerDownloadableMediaMessageProtocolEntity(DownloadableMediaMessageProtocolEntity):
    """
    Entidade para mensagens de sticker.
    
    Herda de DownloadableMediaMessageProtocolEntity e adiciona propriedades específicas de sticker.
    """
    
    def __init__(
        self,
        sticker_attrs: StickerAttributes,
        message_meta_attrs: MessageMetaAttributes
    ):
        """
        Inicializa StickerDownloadableMediaMessageProtocolEntity.
        
        Args:
            sticker_attrs: Atributos de sticker
            message_meta_attrs: Metadados da mensagem
        """
        super(StickerDownloadableMediaMessageProtocolEntity, self).__init__(
            "sticker", MessageAttributes(sticker=sticker_attrs), message_meta_attrs
        )
    
    @property
    def media_specific_attributes(self) -> StickerAttributes:
        """Atributos específicos de sticker."""
        return self.message_attributes.sticker
    
    @property
    def downloadablemedia_specific_attributes(self) -> 'DownloadableMediaMessageAttributes':
        """Atributos de mídia downloadable."""
        return self.message_attributes.sticker.downloadablemedia_attributes
    
    @property
    def width(self) -> int:
        """Largura do sticker em pixels."""
        return self.media_specific_attributes.width
    
    @width.setter
    def width(self, value: int):
        """Define largura do sticker."""
        self.media_specific_attributes.width = value
    
    @property
    def height(self) -> int:
        """Altura do sticker em pixels."""
        return self.media_specific_attributes.height
    
    @height.setter
    def height(self, value: int):
        """Define altura do sticker."""
        self.media_specific_attributes.height = value
    
    @property
    def png_thumbnail(self) -> Optional[bytes]:
        """Thumbnail PNG do sticker."""
        return self.media_specific_attributes.png_thumbnail
    
    @png_thumbnail.setter
    def png_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail PNG."""
        self.media_specific_attributes.png_thumbnail = value
    
    @property
    def is_animated(self) -> bool:
        """Se o sticker é animado."""
        return self.media_specific_attributes.is_animated
    
    @is_animated.setter
    def is_animated(self, value: bool):
        """Define se o sticker é animado."""
        self.media_specific_attributes.is_animated = value
    
    @property
    def sticker_sent_ts(self) -> int:
        """Timestamp de envio do sticker em milissegundos."""
        return self.media_specific_attributes.sticker_sent_ts
    
    @sticker_sent_ts.setter
    def sticker_sent_ts(self, value: int):
        """Define timestamp de envio do sticker."""
        self.media_specific_attributes.sticker_sent_ts = value
    
    @property
    def is_avatar(self) -> bool:
        """Se é um sticker de avatar."""
        return self.media_specific_attributes.is_avatar
    
    @is_avatar.setter
    def is_avatar(self, value: bool):
        """Define se é sticker de avatar."""
        self.media_specific_attributes.is_avatar = value
    
    @property
    def is_ai_sticker(self) -> bool:
        """Se é um sticker gerado por IA."""
        return self.media_specific_attributes.is_ai_sticker
    
    @is_ai_sticker.setter
    def is_ai_sticker(self, value: bool):
        """Define se é sticker gerado por IA."""
        self.media_specific_attributes.is_ai_sticker = value
    
    @property
    def is_lottie(self) -> bool:
        """Se é um sticker Lottie."""
        return self.media_specific_attributes.is_lottie
    
    @is_lottie.setter
    def is_lottie(self, value: bool):
        """Define se é sticker Lottie."""
        self.media_specific_attributes.is_lottie = value

