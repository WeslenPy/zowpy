"""
AudioDownloadableMediaMessageProtocolEntity - Entidade para mensagens de áudio.

Baseado em zowsuplib/yowsup/layers/protocol_media/protocolentities/message_media_downloadable_audio.py
"""

from typing import Optional, TYPE_CHECKING

from .message_media_downloadable import DownloadableMediaMessageProtocolEntity
from ..attributes import AudioAttributes, MessageMetaAttributes, MessageAttributes

if TYPE_CHECKING:
    from ..attributes import DownloadableMediaMessageAttributes


class AudioDownloadableMediaMessageProtocolEntity(DownloadableMediaMessageProtocolEntity):
    """
    Entidade para mensagens de áudio.
    
    Herda de DownloadableMediaMessageProtocolEntity e adiciona propriedades específicas de áudio.
    """
    
    def __init__(
        self,
        audio_attrs: AudioAttributes,
        message_meta_attrs: MessageMetaAttributes
    ):
        """
        Inicializa AudioDownloadableMediaMessageProtocolEntity.
        
        Args:
            audio_attrs: Atributos de áudio
            message_meta_attrs: Metadados da mensagem
        """
        super(AudioDownloadableMediaMessageProtocolEntity, self).__init__(
            "audio", MessageAttributes(audio=audio_attrs), message_meta_attrs
        )
    
    @property
    def media_specific_attributes(self) -> AudioAttributes:
        """Atributos específicos de áudio."""
        return self.message_attributes.audio
    
    @property
    def downloadablemedia_specific_attributes(self) -> 'DownloadableMediaMessageAttributes':
        """Atributos de mídia downloadable."""
        return self.message_attributes.audio.downloadablemedia_attributes
    
    @property
    def seconds(self) -> int:
        """Duração do áudio em segundos."""
        return self.media_specific_attributes.seconds
    
    @seconds.setter
    def seconds(self, value: int):
        """Define duração do áudio."""
        self.media_specific_attributes.seconds = value
    
    @property
    def ptt(self) -> bool:
        """Se é uma mensagem push-to-talk."""
        return self.media_specific_attributes.ptt
    
    @ptt.setter
    def ptt(self, value: bool):
        """Define se é push-to-talk."""
        self.media_specific_attributes.ptt = value
    
    @property
    def streaming_sidecar(self) -> Optional[bytes]:
        """Dados de streaming sidecar."""
        return self.media_specific_attributes.streaming_sidecar
    
    @streaming_sidecar.setter
    def streaming_sidecar(self, value: Optional[bytes]):
        """Define dados de streaming sidecar."""
        self.media_specific_attributes.streaming_sidecar = value
    
    @property
    def waveform(self) -> Optional[bytes]:
        """Dados de waveform para visualização."""
        return self.media_specific_attributes.waveform
    
    @waveform.setter
    def waveform(self, value: Optional[bytes]):
        """Define dados de waveform."""
        self.media_specific_attributes.waveform = value

