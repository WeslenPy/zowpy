"""
VideoDownloadableMediaMessageProtocolEntity - Entidade para mensagens de vídeo.

Baseado em zowsuplib/yowsup/layers/protocol_media/protocolentities/message_media_downloadable_video.py
"""

from typing import Optional, TYPE_CHECKING

from .message_media_downloadable import DownloadableMediaMessageProtocolEntity
from ..attributes import VideoAttributes, MessageMetaAttributes, MessageAttributes

if TYPE_CHECKING:
    from ..attributes import DownloadableMediaMessageAttributes


class VideoDownloadableMediaMessageProtocolEntity(DownloadableMediaMessageProtocolEntity):
    """
    Entidade para mensagens de vídeo.
    
    Herda de DownloadableMediaMessageProtocolEntity e adiciona propriedades específicas de vídeo.
    """
    
    def __init__(
        self,
        video_attrs: VideoAttributes,
        message_meta_attrs: MessageMetaAttributes
    ):
        """
        Inicializa VideoDownloadableMediaMessageProtocolEntity.
        
        Args:
            video_attrs: Atributos de vídeo
            message_meta_attrs: Metadados da mensagem
        """
        super(VideoDownloadableMediaMessageProtocolEntity, self).__init__(
            "video", MessageAttributes(video=video_attrs), message_meta_attrs
        )
    
    @property
    def media_specific_attributes(self) -> VideoAttributes:
        """Atributos específicos de vídeo."""
        return self.message_attributes.video
    
    @property
    def downloadablemedia_specific_attributes(self) -> 'DownloadableMediaMessageAttributes':
        """Atributos de mídia downloadable."""
        return self.message_attributes.video.downloadablemedia_attributes
    
    @property
    def width(self) -> int:
        """Largura do vídeo em pixels."""
        return self.media_specific_attributes.width
    
    @width.setter
    def width(self, value: int):
        """Define largura do vídeo."""
        self.media_specific_attributes.width = value
    
    @property
    def height(self) -> int:
        """Altura do vídeo em pixels."""
        return self.media_specific_attributes.height
    
    @height.setter
    def height(self, value: int):
        """Define altura do vídeo."""
        self.media_specific_attributes.height = value
    
    @property
    def seconds(self) -> int:
        """Duração do vídeo em segundos."""
        return self.media_specific_attributes.seconds
    
    @seconds.setter
    def seconds(self, value: int):
        """Define duração do vídeo."""
        self.media_specific_attributes.seconds = value
    
    @property
    def gif_playback(self) -> Optional[bool]:
        """Se o vídeo é um GIF."""
        return self.media_specific_attributes.gif_playback
    
    @gif_playback.setter
    def gif_playback(self, value: Optional[bool]):
        """Define se o vídeo é um GIF."""
        self.media_specific_attributes.gif_playback = value
    
    @property
    def jpeg_thumbnail(self) -> Optional[bytes]:
        """Thumbnail JPEG do vídeo."""
        return self.media_specific_attributes.jpeg_thumbnail
    
    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail JPEG."""
        self.media_specific_attributes.jpeg_thumbnail = value
    
    @property
    def caption(self) -> Optional[str]:
        """Legenda do vídeo."""
        return self.media_specific_attributes.caption
    
    @caption.setter
    def caption(self, value: Optional[str]):
        """Define legenda do vídeo."""
        self.media_specific_attributes.caption = value
    
    @property
    def gif_attribution(self) -> Optional[int]:
        """Atribuição de GIF."""
        return self.media_specific_attributes.gif_attribution
    
    @gif_attribution.setter
    def gif_attribution(self, value: Optional[int]):
        """Define atribuição de GIF."""
        self.media_specific_attributes.gif_attribution = value
    
    @property
    def streaming_sidecar(self) -> Optional[bytes]:
        """Dados de streaming sidecar."""
        return self.media_specific_attributes.streaming_sidecar
    
    @streaming_sidecar.setter
    def streaming_sidecar(self, value: Optional[bytes]):
        """Define dados de streaming sidecar."""
        self.media_specific_attributes.streaming_sidecar = value

