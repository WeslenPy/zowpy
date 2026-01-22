"""
VideoAttributes - Atributos específicos para vídeos.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_video.py
"""

import os
from typing import Optional, Tuple, Any
from loguru import logger

from .attributes_downloadablemedia import DownloadableMediaMessageAttributes
from ....utils.media_tools import VideoTools, normalize_file_path_or_url


class VideoAttributes:
    """
    Atributos específicos para mensagens de vídeo.
    
    Contém informações sobre dimensões, duração, thumbnail e legenda.
    """
    
    def __init__(
        self,
        downloadablemedia_attributes: DownloadableMediaMessageAttributes,
        width: int,
        height: int,
        seconds: int,
        caption: Optional[str] = None,
        gif_playback: Optional[bool] = None,
        jpeg_thumbnail: Optional[bytes] = None,
        gif_attribution: Optional[int] = None,
        streaming_sidecar: Optional[bytes] = None
    ):
        """
        Inicializa VideoAttributes.
        
        Args:
            downloadablemedia_attributes: Atributos de mídia downloadable
            width: Largura do vídeo em pixels
            height: Altura do vídeo em pixels
            seconds: Duração do vídeo em segundos
            caption: Legenda do vídeo (opcional)
            gif_playback: Se o vídeo é um GIF (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional, bytes)
            gif_attribution: Atribuição de GIF (opcional)
            streaming_sidecar: Dados de streaming sidecar (opcional, bytes)
        """
        self._downloadablemedia_attributes = downloadablemedia_attributes
        self._width = width
        self._height = height
        self._seconds = seconds
        self._caption = caption
        self._gif_playback = gif_playback
        self._jpeg_thumbnail = jpeg_thumbnail
        self._gif_attribution = gif_attribution
        self._streaming_sidecar = streaming_sidecar
    
    def __str__(self):
        attrs = []
        if self.width is not None:
            attrs.append(("width", self.width))
        if self.height is not None:
            attrs.append(("height", self.height))
        if self.seconds is not None:
            attrs.append(("seconds", self.seconds))
        if self.gif_playback is not None:
            attrs.append(("gif_playback", self.gif_playback))
        if self.jpeg_thumbnail is not None:
            attrs.append(("jpeg_thumbnail", "[binary data]"))
        if self.gif_attribution is not None:
            attrs.append(("gif_attribution", self.gif_attribution))
        if self.caption is not None:
            attrs.append(("caption", self.caption))
        if self.streaming_sidecar is not None:
            attrs.append(("streaming_sidecar", "[binary data]"))
        attrs.append(("downloadable", self.downloadablemedia_attributes))
        
        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))
    
    @property
    def downloadablemedia_attributes(self) -> DownloadableMediaMessageAttributes:
        """Atributos de mídia downloadable."""
        return self._downloadablemedia_attributes
    
    @downloadablemedia_attributes.setter
    def downloadablemedia_attributes(self, value: DownloadableMediaMessageAttributes):
        """Define atributos de mídia downloadable."""
        self._downloadablemedia_attributes = value
    
    @property
    def width(self) -> int:
        """Largura do vídeo em pixels."""
        return self._width
    
    @width.setter
    def width(self, value: int):
        """Define largura do vídeo."""
        self._width = value
    
    @property
    def height(self) -> int:
        """Altura do vídeo em pixels."""
        return self._height
    
    @height.setter
    def height(self, value: int):
        """Define altura do vídeo."""
        self._height = value
    
    @property
    def seconds(self) -> int:
        """Duração do vídeo em segundos."""
        return self._seconds
    
    @seconds.setter
    def seconds(self, value: int):
        """Define duração do vídeo."""
        self._seconds = value
    
    @property
    def gif_playback(self) -> Optional[bool]:
        """Se o vídeo é um GIF."""
        return self._gif_playback
    
    @gif_playback.setter
    def gif_playback(self, value: Optional[bool]):
        """Define se o vídeo é um GIF."""
        self._gif_playback = value
    
    @property
    def jpeg_thumbnail(self) -> Optional[bytes]:
        """Thumbnail JPEG do vídeo."""
        return self._jpeg_thumbnail
    
    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail JPEG."""
        self._jpeg_thumbnail = value
    
    @property
    def gif_attribution(self) -> Optional[int]:
        """Atribuição de GIF."""
        return self._gif_attribution
    
    @gif_attribution.setter
    def gif_attribution(self, value: Optional[int]):
        """Define atribuição de GIF."""
        self._gif_attribution = value
    
    @property
    def caption(self) -> Optional[str]:
        """Legenda do vídeo."""
        return self._caption
    
    @caption.setter
    def caption(self, value: Optional[str]):
        """Define legenda do vídeo."""
        self._caption = value
    
    @property
    def streaming_sidecar(self) -> Optional[bytes]:
        """Dados de streaming sidecar."""
        return self._streaming_sidecar
    
    @streaming_sidecar.setter
    def streaming_sidecar(self, value: Optional[bytes]):
        """Define dados de streaming sidecar."""
        self._streaming_sidecar = value
    
    @staticmethod
    async def from_filepath(
        filepath: str,
        media_type: Optional[str] = None,
        result_request_media_conn_iq: Optional[Any] = None,
        video_properties: Optional[Tuple[int, int, Optional[int], int, Optional[str]]] = None,
        caption: Optional[str] = None,
        jpeg_thumbnail: Optional[bytes] = None,
        gif_playback: bool = False,
        gif_attribution: int = 0
    ) -> 'VideoAttributes':
        """
        Cria VideoAttributes a partir de arquivo local.
        
        Args:
            filepath: Caminho do arquivo de vídeo
            media_type: Tipo de mídia (opcional)
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            video_properties: Tupla (width, height, bitrate, seconds, codec) - se None, será detectado automaticamente
            caption: Legenda do vídeo (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional) - se None, será gerado automaticamente
            gif_playback: Se o vídeo é um GIF (padrão: False)
            gif_attribution: Atribuição de GIF (padrão: 0)
        
        Returns:
            VideoAttributes
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {filepath}")
        try:
            if not jpeg_thumbnail:
                jpeg_thumbnail = VideoTools.generate_thumbnail(filepath)
            if not video_properties:
                try:
                    width, height = VideoTools.get_dimensions(filepath)
                    seconds = VideoTools.get_duration(filepath)
                    video_properties = (width, height, None, seconds, None)
                except Exception as e:
                    logger.warning("Erro ao obter propriedades do vídeo: %s", e)
                    video_properties = None
        except Exception as e:
            logger.exception("Erro em media_tools ao processar vídeo (from_filepath): %s", e)
            raise
        
        if video_properties:
            width, height, bitrate, seconds, codec = video_properties
        else:
            width, height, bitrate, seconds, codec = (None, None, None, None, None)
        
        if not width or not height:
            raise ValueError("Could not determine video properties, install VideoStream or pass video_properties")
        
        downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
            filepath, media_type or "video", result_request_media_conn_iq
        )
        
        return VideoAttributes(
            downloadable_attrs, width, height, seconds, caption, gif_playback, jpeg_thumbnail, gif_attribution
        )
    
    @staticmethod
    async def from_url(
        url: str,
        media_type: Optional[str] = None,
        result_request_media_conn_iq: Optional[Any] = None,
        video_properties: Optional[Tuple[int, int, Optional[int], int, Optional[str]]] = None,
        caption: Optional[str] = None,
        jpeg_thumbnail: Optional[bytes] = None,
        gif_playback: bool = False,
        gif_attribution: int = 0
    ) -> 'VideoAttributes':
        """
        Cria VideoAttributes a partir de URL.
        
        Args:
            url: URL do vídeo
            media_type: Tipo de mídia (opcional)
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            video_properties: Tupla (width, height, bitrate, seconds, codec) - se None, será detectado automaticamente
            caption: Legenda do vídeo (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional) - se None, será gerado automaticamente
            gif_playback: Se o vídeo é um GIF (padrão: False)
            gif_attribution: Atribuição de GIF (padrão: 0)
        
        Returns:
            VideoAttributes
        """
        filepath = None
        is_temporary = False
        try:
            filepath, is_temporary = await normalize_file_path_or_url(
                url, default_extension=".mp4", prefix="video"
            )
            if not jpeg_thumbnail:
                jpeg_thumbnail = VideoTools.generate_thumbnail(filepath)
            if not video_properties:
                try:
                    width, height = VideoTools.get_dimensions(filepath)
                    seconds = VideoTools.get_duration(filepath)
                    video_properties = (width, height, None, seconds, None)
                except Exception as e:
                    logger.warning("Erro ao obter propriedades do vídeo: %s", e)
                    video_properties = None
            if video_properties:
                width, height, bitrate, seconds, codec = video_properties
            else:
                width, height, bitrate, seconds, codec = (None, None, None, None, None)
            if not width or not height:
                raise ValueError("Could not determine video properties, install VideoStream or pass video_properties")
            downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
                filepath, media_type or "video", result_request_media_conn_iq
            )
            return VideoAttributes(
                downloadable_attrs, width, height, seconds, caption, gif_playback, jpeg_thumbnail, gif_attribution
            )
        except Exception as e:
            logger.exception("Erro em media_tools ao processar vídeo (from_url): %s", e)
            raise
        finally:
            if is_temporary and filepath:
                try:
                    os.unlink(filepath)
                except Exception as ex:
                    logger.warning("Erro ao remover arquivo temporário %s: %s", filepath, ex)

