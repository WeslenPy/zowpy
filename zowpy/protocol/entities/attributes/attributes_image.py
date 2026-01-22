"""
ImageAttributes - Atributos específicos para imagens.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_image.py
"""

import os
from typing import Optional, Tuple, Any
from loguru import logger

from .attributes_downloadablemedia import DownloadableMediaMessageAttributes
from ....utils.media_tools import ImageTools, normalize_file_path_or_url


class ImageAttributes:
    """
    Atributos específicos para mensagens de imagem.
    
    Contém informações sobre dimensões, thumbnail e legenda.
    """
    
    def __init__(
        self,
        downloadablemedia_attributes: DownloadableMediaMessageAttributes,
        width: int,
        height: int,
        caption: Optional[str] = None,
        jpeg_thumbnail: Optional[bytes] = None
    ):
        """
        Inicializa ImageAttributes.
        
        Args:
            downloadablemedia_attributes: Atributos de mídia downloadable
            width: Largura da imagem em pixels
            height: Altura da imagem em pixels
            caption: Legenda da imagem (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional, bytes)
        """
        self._downloadablemedia_attributes = downloadablemedia_attributes
        self._width = width
        self._height = height
        self._caption = caption
        self._jpeg_thumbnail = jpeg_thumbnail
    
    def __str__(self):
        attrs = []
        if self.width is not None:
            attrs.append(("width", self.width))
        if self.height is not None:
            attrs.append(("height", self.height))
        if self.caption is not None:
            attrs.append(("caption", self.caption))
        if self.jpeg_thumbnail is not None:
            attrs.append(("jpeg_thumbnail", "[binary data]"))
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
        """Largura da imagem em pixels."""
        return self._width
    
    @width.setter
    def width(self, value: int):
        """Define largura da imagem."""
        self._width = value
    
    @property
    def height(self) -> int:
        """Altura da imagem em pixels."""
        return self._height
    
    @height.setter
    def height(self, value: int):
        """Define altura da imagem."""
        self._height = value
    
    @property
    def caption(self) -> Optional[str]:
        """Legenda da imagem."""
        return self._caption
    
    @caption.setter
    def caption(self, value: Optional[str]):
        """Define legenda da imagem."""
        self._caption = value if value else ''
    
    @property
    def jpeg_thumbnail(self) -> Optional[bytes]:
        """Thumbnail JPEG da imagem."""
        return self._jpeg_thumbnail
    
    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail JPEG."""
        self._jpeg_thumbnail = value if value else b''
    
    @staticmethod
    async def from_filepath(
        filepath: str,
        media_type: Optional[str] = None,
        result_request_media_conn_iq: Optional[Any] = None,
        dimensions: Optional[Tuple[int, int]] = None,
        caption: Optional[str] = None,
        jpeg_thumbnail: Optional[bytes] = None
    ) -> 'ImageAttributes':
        """
        Cria ImageAttributes a partir de arquivo local.
        
        Args:
            filepath: Caminho do arquivo de imagem
            media_type: Tipo de mídia (opcional)
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            dimensions: Tupla (width, height) - se None, será detectado automaticamente
            caption: Legenda da imagem (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional) - se None, será gerado automaticamente
        
        Returns:
            ImageAttributes
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo de imagem não encontrado: {filepath}")
        
        try:
            if not jpeg_thumbnail:
                jpeg_thumbnail = ImageTools.generate_thumbnail(filepath)
            dimensions = dimensions or ImageTools.get_dimensions(filepath)
        except Exception as e:
            logger.exception("Erro em media_tools ao processar imagem (from_filepath): %s", e)
            raise
        width, height = dimensions if dimensions else (None, None)
        
        if not width or not height:
            raise ValueError("Could not determine image dimensions, install pillow or pass dimensions")
        
        downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
            filepath, media_type or "image", result_request_media_conn_iq
        )
        
        return ImageAttributes(
            downloadable_attrs, width, height, caption, jpeg_thumbnail
        )
    
    @staticmethod
    async def from_url(
        url: str,
        media_type: Optional[str] = None,
        result_request_media_conn_iq: Optional[Any] = None,
        dimensions: Optional[Tuple[int, int]] = None,
        caption: Optional[str] = None,
        jpeg_thumbnail: Optional[bytes] = None
    ) -> 'ImageAttributes':
        """
        Cria ImageAttributes a partir de URL.
        
        Args:
            url: URL da imagem
            media_type: Tipo de mídia (opcional)
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            dimensions: Tupla (width, height) - se None, será detectado automaticamente
            caption: Legenda da imagem (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional) - se None, será gerado automaticamente
        
        Returns:
            ImageAttributes
        """
        filepath = None
        is_temporary = False
        try:
            filepath, is_temporary = await normalize_file_path_or_url(
                url, default_extension=".jpg", prefix="image"
            )
            if not jpeg_thumbnail:
                jpeg_thumbnail = ImageTools.generate_thumbnail(filepath)
            dimensions = dimensions or ImageTools.get_dimensions(filepath)
            width, height = dimensions if dimensions else (None, None)
            if not width or not height:
                raise ValueError("Could not determine image dimensions, install pillow or pass dimensions")
            downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
                filepath, media_type or "image", result_request_media_conn_iq
            )
            return ImageAttributes(
                downloadable_attrs, width, height, caption, jpeg_thumbnail
            )
        except Exception as e:
            logger.exception("Erro em media_tools ao processar imagem (from_url): %s", e)
            raise
        finally:
            if is_temporary and filepath:
                try:
                    os.unlink(filepath)
                except Exception as ex:
                    logger.warning("Erro ao remover arquivo temporário %s: %s", filepath, ex)

