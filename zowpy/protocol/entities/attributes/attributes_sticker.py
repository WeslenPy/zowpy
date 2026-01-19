"""
StickerAttributes - Atributos específicos para stickers.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_sticker.py
"""

import os
import time
from typing import Optional, Tuple, Any
from loguru import logger

from .attributes_downloadablemedia import DownloadableMediaMessageAttributes
from ....utils.media_tools import ImageTools, normalize_file_path_or_url


class StickerAttributes:
    """
    Atributos específicos para mensagens de sticker.
    
    Contém informações sobre dimensões, thumbnail PNG e flags especiais.
    """
    
    def __init__(
        self,
        downloadablemedia_attributes: DownloadableMediaMessageAttributes,
        width: int,
        height: int,
        png_thumbnail: Optional[bytes] = None,
        is_animated: bool = False,
        sticker_sent_ts: Optional[int] = None,
        is_avatar: bool = False,
        is_ai_sticker: bool = False,
        is_lottie: bool = False
    ):
        """
        Inicializa StickerAttributes.
        
        Args:
            downloadablemedia_attributes: Atributos de mídia downloadable
            width: Largura do sticker em pixels
            height: Altura do sticker em pixels
            png_thumbnail: Thumbnail PNG (opcional, bytes)
            is_animated: Se o sticker é animado (padrão: False)
            sticker_sent_ts: Timestamp de envio do sticker em milissegundos (opcional, usa timestamp atual se None)
            is_avatar: Se é um sticker de avatar (padrão: False)
            is_ai_sticker: Se é um sticker gerado por IA (padrão: False)
            is_lottie: Se é um sticker Lottie (padrão: False)
        """
        self._downloadablemedia_attributes = downloadablemedia_attributes
        self._width = width
        self._height = height
        self._png_thumbnail = png_thumbnail
        self._is_animated = is_animated
        self._sticker_sent_ts = int(sticker_sent_ts) if sticker_sent_ts is not None else int(time.time() * 1000)  # em milissegundos
        self._is_avatar = is_avatar
        self._is_ai_sticker = is_ai_sticker
        self._is_lottie = is_lottie
    
    def __str__(self):
        attrs = []
        if self.width is not None:
            attrs.append(("width", self.width))
        if self.height is not None:
            attrs.append(("height", self.height))
        if self.png_thumbnail is not None:
            attrs.append(("png_thumbnail", "[binary data]"))
        if self.is_animated is not None:
            attrs.append(("is_animated", self.is_animated))
        if self.is_avatar is not None:
            attrs.append(("is_avatar", self.is_avatar))
        if self.is_ai_sticker is not None:
            attrs.append(("is_ai_sticker", self.is_ai_sticker))
        if self.is_lottie is not None:
            attrs.append(("is_lottie", self.is_lottie))
        if self.sticker_sent_ts is not None:
            attrs.append(("sticker_sent_ts", self.sticker_sent_ts))
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
        """Largura do sticker em pixels."""
        return self._width
    
    @width.setter
    def width(self, value: int):
        """Define largura do sticker."""
        self._width = value
    
    @property
    def height(self) -> int:
        """Altura do sticker em pixels."""
        return self._height
    
    @height.setter
    def height(self, value: int):
        """Define altura do sticker."""
        self._height = value
    
    @property
    def png_thumbnail(self) -> Optional[bytes]:
        """Thumbnail PNG do sticker."""
        return self._png_thumbnail
    
    @png_thumbnail.setter
    def png_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail PNG."""
        self._png_thumbnail = value
    
    @property
    def is_avatar(self) -> bool:
        """Se é um sticker de avatar."""
        return self._is_avatar
    
    @is_avatar.setter
    def is_avatar(self, value: bool):
        """Define se é sticker de avatar."""
        self._is_avatar = value
    
    @property
    def is_animated(self) -> bool:
        """Se o sticker é animado."""
        return self._is_animated
    
    @is_animated.setter
    def is_animated(self, value: bool):
        """Define se o sticker é animado."""
        self._is_animated = value
    
    @property
    def is_ai_sticker(self) -> bool:
        """Se é um sticker gerado por IA."""
        return self._is_ai_sticker
    
    @is_ai_sticker.setter
    def is_ai_sticker(self, value: bool):
        """Define se é sticker gerado por IA."""
        self._is_ai_sticker = value
    
    @property
    def is_lottie(self) -> bool:
        """Se é um sticker Lottie."""
        return self._is_lottie
    
    @is_lottie.setter
    def is_lottie(self, value: bool):
        """Define se é sticker Lottie."""
        self._is_lottie = value
    
    @property
    def sticker_sent_ts(self) -> int:
        """Timestamp de envio do sticker em milissegundos."""
        return self._sticker_sent_ts
    
    @sticker_sent_ts.setter
    def sticker_sent_ts(self, value: int):
        """Define timestamp de envio do sticker."""
        self._sticker_sent_ts = value
    
    @staticmethod
    async def from_filepath(
        filepath: str,
        media_type: str = "sticker",
        result_request_media_conn_iq: Optional[Any] = None,
        dimensions: Optional[Tuple[int, int]] = None,
        png_thumbnail: Optional[bytes] = None,
        is_animated: bool = False,
        is_avatar: bool = False,
        is_ai_sticker: bool = False,
        is_lottie: bool = False
    ) -> 'StickerAttributes':
        """
        Cria StickerAttributes a partir de arquivo local.
        
        Args:
            filepath: Caminho do arquivo do sticker
            media_type: Tipo de mídia (padrão: "sticker")
            result_request_media_conn_iq: Entidade de conexão de mídia (opcional)
            dimensions: Tupla (width, height) - se None, será detectado automaticamente
            png_thumbnail: Thumbnail PNG (bytes) - se None, será gerado automaticamente
            is_animated: Se o sticker é animado
            is_avatar: Se é um sticker de avatar
            is_ai_sticker: Se é um sticker gerado por IA
            is_lottie: Se é um sticker Lottie
        
        Returns:
            StickerAttributes
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        # Obtém dimensões se não fornecidas
        if not dimensions:
            dimensions = ImageTools.get_dimensions(filepath)
        
        width, height = dimensions if dimensions else (512, 512)  # Default para stickers
        
        # Gera thumbnail PNG se não fornecido (sticker usa PNG, não JPEG)
        # Por enquanto, deixamos None e o WhatsApp pode gerar
        if not png_thumbnail:
            png_thumbnail = None
        
        downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
            filepath, media_type, result_request_media_conn_iq
        )
        
        return StickerAttributes(
            downloadable_attrs, width, height, png_thumbnail, is_animated, None, is_avatar, is_ai_sticker, is_lottie
        )
    
    @staticmethod
    async def from_url(
        url: str,
        media_type: str = "sticker",
        result_request_media_conn_iq: Optional[Any] = None,
        dimensions: Optional[Tuple[int, int]] = None,
        png_thumbnail: Optional[bytes] = None,
        is_animated: bool = False,
        is_avatar: bool = False,
        is_ai_sticker: bool = False,
        is_lottie: bool = False
    ) -> 'StickerAttributes':
        """
        Cria StickerAttributes a partir de URL.
        
        Args:
            url: URL do sticker
            media_type: Tipo de mídia (padrão: "sticker")
            result_request_media_conn_iq: Entidade de conexão de mídia (opcional)
            dimensions: Tupla (width, height) - se None, será detectado automaticamente
            png_thumbnail: Thumbnail PNG (bytes) - se None, será gerado automaticamente
            is_animated: Se o sticker é animado
            is_avatar: Se é um sticker de avatar
            is_ai_sticker: Se é um sticker gerado por IA
            is_lottie: Se é um sticker Lottie
        
        Returns:
            StickerAttributes
        """
        # Baixa arquivo temporariamente
        filepath, is_temporary = await normalize_file_path_or_url(
            url, default_extension=".webp", prefix="sticker"
        )
        
        try:
            # Obtém dimensões se não fornecidas
            if not dimensions:
                dimensions = ImageTools.get_dimensions(filepath)
            
            width, height = dimensions if dimensions else (512, 512)  # Default para stickers
            
            # Gera thumbnail PNG se não fornecido
            if not png_thumbnail:
                png_thumbnail = None
            
            downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
                filepath, media_type, result_request_media_conn_iq
            )
            
            return StickerAttributes(
                downloadable_attrs, width, height, png_thumbnail, is_animated, None, is_avatar, is_ai_sticker, is_lottie
            )
        finally:
            # Remove arquivo temporário
            if is_temporary:
                try:
                    os.unlink(filepath)
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo temporário {filepath}: {e}")

