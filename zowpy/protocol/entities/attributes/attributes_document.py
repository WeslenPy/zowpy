"""
DocumentAttributes - Atributos específicos para documentos.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_document.py
"""

import os
from typing import Optional, Any
from loguru import logger

from .attributes_downloadablemedia import DownloadableMediaMessageAttributes
from ....utils.media_tools import normalize_file_path_or_url


class DocumentAttributes:
    """
    Atributos específicos para mensagens de documento.
    
    Contém informações sobre nome do arquivo, tamanho, título, páginas e thumbnail.
    """
    
    def __init__(
        self,
        downloadablemedia_attributes: DownloadableMediaMessageAttributes,
        file_name: str,
        file_length: int,
        title: Optional[str] = None,
        page_count: Optional[int] = None,
        jpeg_thumbnail: Optional[bytes] = None,
        caption: Optional[str] = None
    ):
        """
        Inicializa DocumentAttributes.
        
        Args:
            downloadablemedia_attributes: Atributos de mídia downloadable
            file_name: Nome do arquivo
            file_length: Tamanho do arquivo em bytes
            title: Título do documento (opcional)
            page_count: Número de páginas (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional, bytes)
            caption: Legenda do documento (opcional)
        """
        self._downloadablemedia_attributes = downloadablemedia_attributes
        self._file_name = file_name
        self._file_length = file_length
        self._title = title
        self._page_count = page_count
        self._jpeg_thumbnail = jpeg_thumbnail
        self._caption = caption
    
    def __str__(self):
        attrs = []
        if self.file_name is not None:
            attrs.append(("file_name", self.file_name))
        if self.file_length is not None:
            attrs.append(("file_length", self.file_length))
        if self.title is not None:
            attrs.append(("title", self.title))
        if self.page_count is not None:
            attrs.append(("page_count", self.page_count))
        if self.jpeg_thumbnail is not None:
            attrs.append(("jpeg_thumbnail", "[binary data]"))
        if self.caption is not None:
            attrs.append(("caption", self.caption))
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
    def caption(self) -> Optional[str]:
        """Legenda do documento."""
        return self._caption
    
    @caption.setter
    def caption(self, value: Optional[str]):
        """Define legenda do documento."""
        self._caption = value
    
    @property
    def file_name(self) -> str:
        """Nome do arquivo."""
        return self._file_name
    
    @file_name.setter
    def file_name(self, value: str):
        """Define nome do arquivo."""
        self._file_name = value
    
    @property
    def file_length(self) -> int:
        """Tamanho do arquivo em bytes."""
        return self._file_length
    
    @file_length.setter
    def file_length(self, value: int):
        """Define tamanho do arquivo."""
        self._file_length = value
    
    @property
    def title(self) -> Optional[str]:
        """Título do documento."""
        return self._title
    
    @title.setter
    def title(self, value: Optional[str]):
        """Define título do documento."""
        self._title = value
    
    @property
    def page_count(self) -> Optional[int]:
        """Número de páginas."""
        return self._page_count
    
    @page_count.setter
    def page_count(self, value: Optional[int]):
        """Define número de páginas."""
        self._page_count = value
    
    @property
    def jpeg_thumbnail(self) -> Optional[bytes]:
        """Thumbnail JPEG do documento."""
        return self._jpeg_thumbnail
    
    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value: Optional[bytes]):
        """Define thumbnail JPEG."""
        self._jpeg_thumbnail = value
    
    @staticmethod
    async def from_filepath(
        filepath: str,
        file_name: Optional[str] = None,
        media_type: Optional[str] = None,
        result_request_media_conn_iq: Optional[Any] = None,
        title: Optional[str] = None,
        page_count: Optional[int] = None,
        jpeg_thumbnail: Optional[bytes] = None,
        caption: Optional[str] = None
    ) -> 'DocumentAttributes':
        """
        Cria DocumentAttributes a partir de arquivo local.
        
        Args:
            filepath: Caminho do arquivo de documento
            file_name: Nome do arquivo (opcional, usa basename se None)
            media_type: Tipo de mídia (opcional)
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            title: Título do documento (opcional)
            page_count: Número de páginas (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional)
            caption: Legenda do documento (opcional)
        
        Returns:
            DocumentAttributes
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo de documento não encontrado: {filepath}")
        
        downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
            filepath, media_type or "document", result_request_media_conn_iq
        )
        
        return DocumentAttributes(
            downloadable_attrs,
            os.path.basename(filepath) if file_name is None else file_name,
            os.path.getsize(filepath),
            title,
            page_count,
            jpeg_thumbnail,
            caption
        )
    
    @staticmethod
    async def from_url(
        url: str,
        file_name: Optional[str] = None,
        media_type: Optional[str] = None,
        result_request_media_conn_iq: Optional[Any] = None,
        title: Optional[str] = None,
        page_count: Optional[int] = None,
        jpeg_thumbnail: Optional[bytes] = None,
        caption: Optional[str] = None
    ) -> 'DocumentAttributes':
        """
        Cria DocumentAttributes a partir de URL.
        
        Args:
            url: URL do documento
            file_name: Nome do arquivo (opcional)
            media_type: Tipo de mídia (opcional)
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            title: Título do documento (opcional)
            page_count: Número de páginas (opcional)
            jpeg_thumbnail: Thumbnail JPEG (opcional)
            caption: Legenda do documento (opcional)
        
        Returns:
            DocumentAttributes
        """
        filepath = None
        is_temporary = False
        try:
            filepath, is_temporary = await normalize_file_path_or_url(
                url, default_extension=".bin", prefix="document"
            )
            downloadable_attrs = await DownloadableMediaMessageAttributes.from_file(
                filepath, media_type or "document", result_request_media_conn_iq
            )
            return DocumentAttributes(
                downloadable_attrs,
                os.path.basename(filepath) if file_name is None else file_name,
                os.path.getsize(filepath),
                title,
                page_count,
                jpeg_thumbnail,
                caption
            )
        except Exception as e:
            logger.exception("Erro em media_tools ao processar documento (from_url): %s", e)
            raise
        finally:
            if is_temporary and filepath:
                try:
                    os.unlink(filepath)
                except Exception as ex:
                    logger.warning("Erro ao remover arquivo temporário %s: %s", filepath, ex)

