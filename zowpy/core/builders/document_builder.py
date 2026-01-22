"""
Document Builder - Constrói DocumentMessage protobuf para envio de documentos.
"""

import os
import time
import hashlib
from typing import Optional
from loguru import logger

from ...utils.media_tools import MimeTools, DocumentMetadata, ImageTools, normalize_file_path_or_url
from ...utils.tools import WATools
from ...core.media.media_cipher import MediaCipher
from ...core.media.media_uploader import AsyncMediaUploader
from ...core.media.media_connection import MediaConnection


class DocumentBuilder:
    """Constrói DocumentMessage protobuf para envio de documentos."""
    
    def __init__(
        self,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection
    ):
        """Inicializa DocumentBuilder."""
        self._media_cipher = media_cipher
        self._media_uploader = media_uploader
        self._media_connection = media_connection
    
    @classmethod
    async def from_filepath(
        cls,
        file_path_or_url: str,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> 'DocumentBuilder':
        """Cria DocumentBuilder a partir de arquivo ou URL."""
        filepath = None
        is_temporary = False
        try:
            filepath, is_temporary = await normalize_file_path_or_url(
                file_path_or_url,
                default_extension=".bin",
                prefix="document"
            )
            mimetype = MimeTools.get_mime(filepath)
            file_name = filename or os.path.basename(filepath)
            with open(filepath, 'rb') as f:
                file_data = f.read()
            file_length = len(file_data)
            file_sha256 = hashlib.sha256(file_data).digest()
            jpeg_thumbnail = None
            try:
                if mimetype.startswith("image/"):
                    jpeg_thumbnail = ImageTools.generate_thumbnail(filepath) if hasattr(ImageTools, 'generate_thumbnail') else None
            except Exception as ex:
                logger.debug("Erro ao gerar thumbnail para documento: %s", ex)
            builder = cls(media_cipher, media_uploader, media_connection)
            builder._filepath = filepath
            builder._is_temporary = is_temporary
            builder._mimetype = mimetype
            builder._file_name = file_name
            builder._file_length = file_length
            builder._file_sha256 = file_sha256
            builder._caption = caption
            builder._jpeg_thumbnail = jpeg_thumbnail
            builder._progress_callback = progress_callback
            return builder
        except Exception as e:
            logger.exception("Erro em media_tools ao processar documento (DocumentBuilder.from_filepath): %s", e)
            if is_temporary and filepath:
                try:
                    os.unlink(filepath)
                except Exception:
                    pass
            raise
    
    async def upload_and_build(
        self,
        to_jid: str,
        from_jid: str
    ) -> 'DocumentMessage':
        """Faz upload e constrói DocumentMessage protobuf completo."""
        if not hasattr(self, '_filepath'):
            raise RuntimeError("DocumentBuilder não foi inicializado com filepath")
        
        # 1. Lê arquivo
        with open(self._filepath, 'rb') as f:
            file_data = f.read()
        
        # 2. Gera media_key (formato compatível com zowsuplib)
        self._media_key = WATools.generate_media_key()
        self._media_key_timestamp = int(time.time())
        
        # 3. Criptografa documento
        encrypted_data = self._media_cipher.encrypt_document(file_data, self._media_key)
        # Bytes raw (32 bytes) - protobuf espera bytes, não base64
        self._file_enc_sha256 = hashlib.sha256(encrypted_data).digest()
        
        # 4. Obtém media connection
        media_conn = await self._media_connection.get_connection()
        hosts = media_conn["hosts"]
        auth = media_conn["auth"]
        
        # Seleciona primeiro host (como zowsup: getHosts()[0])
        host = hosts[0] if hosts else None
        if not host:
            raise RuntimeError("Nenhum host disponível na media connection")
        
        # Constrói upload URL
        # IMPORTANTE: usa hash dos DADOS CRIPTOGRAFADOS, não dos originais (como zowsup)
        b64Hash = WATools.getDataHashForUpload(encrypted_data)
        b64Hash_urlsafe = b64Hash.replace('+', '-').replace('/', '_').replace('=', '')
        upload_url = f"https://{host}/mms/document/{b64Hash_urlsafe}?auth={auth}&token={b64Hash_urlsafe}"
        
        # 5. Faz upload
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(encrypted_data)
            tmp_encrypted_path = tmp_file.name
        
        try:
            upload_result = await self._media_uploader.upload(
                filepath=tmp_encrypted_path,
                upload_url=upload_url,
                progress_callback=self._progress_callback
            )
            self._upload_result = upload_result
            self._direct_path = upload_result.get("direct_path", "")
        finally:
            try:
                os.unlink(tmp_encrypted_path)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
        
        # 6. Constrói DocumentMessage
        from ...proto.e2e_pb2 import Message
        
        doc_msg = Message.DocumentMessage()
        doc_msg.url = self._upload_result["url"]
        doc_msg.mimetype = self._mimetype
        doc_msg.file_name = self._file_name
        doc_msg.file_sha256 = self._file_sha256
        doc_msg.file_length = self._file_length
        # media_key já é bytes raw (32 bytes) - protobuf espera bytes, não base64
        doc_msg.media_key = self._media_key
        doc_msg.media_key_timestamp = self._media_key_timestamp
        doc_msg.file_enc_sha256 = self._file_enc_sha256
        
        if self._direct_path:
            doc_msg.direct_path = self._direct_path
        
        if self._caption:
            doc_msg.caption = self._caption
        
        if self._jpeg_thumbnail:
            doc_msg.jpeg_thumbnail = self._jpeg_thumbnail
        
        # Limpa arquivo temporário se foi baixado de URL
        if hasattr(self, '_is_temporary') and self._is_temporary:
            try:
                os.unlink(self._filepath)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
        
        return doc_msg

