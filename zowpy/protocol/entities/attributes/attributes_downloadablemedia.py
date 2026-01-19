"""
DownloadableMediaMessageAttributes - Atributos para mídia que pode ser baixada.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_downloadablemedia.py
"""

import base64
import hashlib
import os
import random
import time
from typing import Optional, Any
from loguru import logger

from .attributes_media import MediaAttributes, ContextInfoAttributes


class DownloadableMediaMessageAttributes(MediaAttributes):
    """
    Atributos para mensagens de mídia que podem ser baixadas.
    
    Contém informações sobre o arquivo, criptografia e upload.
    """
    
    MEDIA_PATH = {
        "image": '/mms/image',
        "video": '/mms/video',
        "document": '/mms/document',
        "audio": '/mms/audio',
        "sticker": '/mms/image',
        'thumbnail-link': '/mms/image',
        'product-catalog-image': '/product/image',
        'md-app-state': '/mms/md-app-state',
        'history-sync': '/mms/md-msg-hist'
    }
    
    def __init__(
        self,
        mimetype: Optional[str],
        file_length: int,
        file_sha256: bytes,
        media_key: Optional[bytes] = None,
        media_key_timestamp: Optional[int] = None,
        file_enc_sha256: Optional[bytes] = None,
        url: Optional[str] = None,
        direct_path: Optional[str] = None,
        context_info: Optional[ContextInfoAttributes] = None
    ):
        """
        Inicializa DownloadableMediaMessageAttributes.
        
        Args:
            mimetype: Tipo MIME da mídia
            file_length: Tamanho do arquivo em bytes
            file_sha256: Hash SHA256 do arquivo original (32 bytes)
            media_key: Chave de mídia para criptografia (32 bytes)
            media_key_timestamp: Timestamp da media_key
            file_enc_sha256: Hash SHA256 dos dados criptografados (32 bytes)
            url: URL da mídia no servidor WhatsApp
            direct_path: Caminho direto da mídia
            context_info: Informações de contexto
        """
        super(DownloadableMediaMessageAttributes, self).__init__(context_info)
        self._mimetype = mimetype
        self._file_length = file_length
        self._file_sha256 = file_sha256
        self._media_key = media_key
        self._media_key_timestamp = media_key_timestamp
        self._file_enc_sha256 = file_enc_sha256
        self._url = url
        self._direct_path = direct_path
    
    def __str__(self):
        return "[mimetype=%s, file_length=%d, file_sha256=%s, media_key=%s, media_key_timestamp=%s, file_enc_sha256=%s, url=%s, direct_path=%s]" % (
            self.mimetype,
            self.file_length,
            base64.b64encode(self.file_sha256).decode() if self.file_sha256 else None,
            base64.b64encode(self.media_key).decode() if self.media_key else None,
            str(self.media_key_timestamp),
            base64.b64encode(self.file_enc_sha256).decode() if self.file_enc_sha256 else None,
            self.url,
            self.direct_path
        )
    
    @property
    def url(self) -> Optional[str]:
        """URL da mídia no servidor WhatsApp."""
        return self._url
    
    @url.setter
    def url(self, value: Optional[str]):
        """Define URL da mídia."""
        self._url = value
    
    @property
    def mimetype(self) -> Optional[str]:
        """Tipo MIME da mídia."""
        return self._mimetype
    
    @mimetype.setter
    def mimetype(self, value: Optional[str]):
        """Define tipo MIME."""
        self._mimetype = value
    
    @property
    def file_length(self) -> int:
        """Tamanho do arquivo em bytes."""
        return self._file_length
    
    @file_length.setter
    def file_length(self, value: int):
        """Define tamanho do arquivo."""
        self._file_length = value
    
    @property
    def file_sha256(self) -> bytes:
        """Hash SHA256 do arquivo original (32 bytes)."""
        return self._file_sha256
    
    @file_sha256.setter
    def file_sha256(self, value: bytes):
        """Define hash SHA256 do arquivo."""
        self._file_sha256 = value
    
    @property
    def media_key(self) -> Optional[bytes]:
        """Chave de mídia para criptografia (32 bytes)."""
        return self._media_key
    
    @media_key.setter
    def media_key(self, value: Optional[bytes]):
        """Define chave de mídia."""
        self._media_key = value
    
    @property
    def media_key_timestamp(self) -> Optional[int]:
        """Timestamp da media_key."""
        return self._media_key_timestamp
    
    @media_key_timestamp.setter
    def media_key_timestamp(self, value: Optional[int]):
        """Define timestamp da media_key."""
        self._media_key_timestamp = value
    
    @property
    def file_enc_sha256(self) -> Optional[bytes]:
        """Hash SHA256 dos dados criptografados (32 bytes)."""
        return self._file_enc_sha256
    
    @file_enc_sha256.setter
    def file_enc_sha256(self, value: Optional[bytes]):
        """Define hash SHA256 dos dados criptografados."""
        self._file_enc_sha256 = value
    
    @property
    def direct_path(self) -> Optional[str]:
        """Caminho direto da mídia."""
        return self._direct_path
    
    @direct_path.setter
    def direct_path(self, value: Optional[str]):
        """Define caminho direto da mídia."""
        self._direct_path = value
    
    @staticmethod
    async def from_buffer(
        data: bytes,
        media_type: str,
        result_request_media_conn_iq: Optional[Any] = None,
        context_info: Optional[ContextInfoAttributes] = None
    ) -> 'DownloadableMediaMessageAttributes':
        """
        Cria DownloadableMediaMessageAttributes a partir de buffer de dados.
        
        Nota: Este método faz upload se result_request_media_conn_iq for fornecido.
        Para uso no zowpy, o upload deve ser feito separadamente.
        
        Args:
            data: Dados do arquivo (bytes)
            media_type: Tipo de mídia ("image", "video", "audio", "document", "sticker")
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            context_info: Informações de contexto (opcional)
        
        Returns:
            DownloadableMediaMessageAttributes
        """
        file_sha256 = hashlib.sha256(data).digest()
        
        # Se result_request_media_conn_iq for fornecido, faz upload
        # Por enquanto, retorna apenas os atributos sem upload
        # O upload deve ser feito separadamente no zowpy
        media_key = None
        media_key_timestamp = None
        file_enc_sha256 = None
        url = None
        direct_path = None
        
        if result_request_media_conn_iq is not None:
            # TODO: Implementar upload se necessário
            # Por enquanto, apenas gera media_key
            alp = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            media_key = ''.join(random.sample(alp, 32)).encode("utf-8")
            media_key_timestamp = int(time.time())
        
        return DownloadableMediaMessageAttributes(
            mimetype=None,
            file_length=len(data),
            file_sha256=file_sha256,
            media_key=media_key,
            media_key_timestamp=media_key_timestamp,
            file_enc_sha256=file_enc_sha256,
            url=url,
            direct_path=direct_path,
            context_info=context_info
        )
    
    @staticmethod
    async def from_file(
        filepath: str,
        media_type: str,
        result_request_media_conn_iq: Optional[Any] = None,
        context_info: Optional[ContextInfoAttributes] = None
    ) -> 'DownloadableMediaMessageAttributes':
        """
        Cria DownloadableMediaMessageAttributes a partir de arquivo.
        
        Args:
            filepath: Caminho do arquivo
            media_type: Tipo de mídia
            result_request_media_conn_iq: Resultado da requisição de conexão de mídia (opcional)
            context_info: Informações de contexto (opcional)
        
        Returns:
            DownloadableMediaMessageAttributes
        """
        # Detecta mimetype
        import mimetypes
        mimetype, _ = mimetypes.guess_type(filepath)
        if not mimetype:
            # Fallback baseado em extensão
            ext = os.path.splitext(filepath)[1].lower()
            mimetype_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.mp4': 'video/mp4',
                '.ogg': 'audio/ogg',
                '.opus': 'audio/ogg; codecs=opus',
            }
            mimetype = mimetype_map.get(ext, 'application/octet-stream')
        
        # Normaliza mimetype de áudio
        if "audio" in mimetype:
            mimetype = "audio/ogg; codecs=opus"
        
        file_length = os.path.getsize(filepath)
        
        # Lê arquivo
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Cria atributos a partir do buffer
        res = await DownloadableMediaMessageAttributes.from_buffer(
            data, media_type, result_request_media_conn_iq, context_info
        )
        
        # Atualiza mimetype e file_length
        res.mimetype = mimetype
        res.file_length = file_length
        
        return res

