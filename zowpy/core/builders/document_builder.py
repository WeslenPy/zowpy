"""
Document Builder - Constrói DocumentMessage protobuf para envio de documentos.
"""

import os
import time
import hashlib
import secrets
from typing import Optional
from loguru import logger

from ...utils.media_tools import MimeTools, DocumentMetadata, ImageTools
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
        filepath: str,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> 'DocumentBuilder':
        """Cria DocumentBuilder a partir de arquivo."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        # Processa documento
        mimetype = MimeTools.get_mime(filepath)
        file_name = filename or os.path.basename(filepath)
        
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        file_length = len(file_data)
        file_sha256 = hashlib.sha256(file_data).digest()
        
        # Tenta gerar thumbnail se for imagem/PDF
        jpeg_thumbnail = None
        try:
            if mimetype.startswith("image/"):
                jpeg_thumbnail = ImageTools.generate_thumbnail(filepath) if hasattr(ImageTools, 'generate_thumbnail') else None
        except Exception as e:
            logger.debug(f"Erro ao gerar thumbnail para documento: {e}")
        
        builder = cls(media_cipher, media_uploader, media_connection)
        builder._filepath = filepath
        builder._mimetype = mimetype
        builder._file_name = file_name
        builder._file_length = file_length
        builder._file_sha256 = file_sha256
        builder._caption = caption
        builder._jpeg_thumbnail = jpeg_thumbnail
        builder._progress_callback = progress_callback
        
        return builder
    
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
        
        # 2. Gera media_key
        self._media_key = secrets.token_bytes(32)
        self._media_key_timestamp = int(time.time())
        
        # 3. Criptografa documento
        encrypted_data = self._media_cipher.encrypt_document(file_data, self._media_key)
        self._file_enc_sha256 = hashlib.sha256(encrypted_data).digest()
        
        # 4. Obtém media connection
        media_conn = await self._media_connection.get_connection()
        hosts = media_conn["hosts"]
        auth = media_conn["auth"]
        
        import random
        host = random.choice(hosts) if hosts else None
        if not host:
            raise RuntimeError("Nenhum host disponível na media connection")
        
        # Constrói upload URL
        file_hash_base64 = hashlib.sha256(file_data).hexdigest()[:32]
        upload_url = f"https://{host}/mms/document/{file_hash_base64}?auth={auth}&token={file_hash_base64}"
        
        # 5. Faz upload
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(encrypted_data)
            tmp_encrypted_path = tmp_file.name
        
        try:
            upload_result = await self._media_uploader.upload(
                filepath=tmp_encrypted_path,
                upload_url=upload_url,
                to_jid=to_jid,
                from_jid=from_jid,
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
        from ...proto.e2e_pb2 import DocumentMessage
        
        doc_msg = DocumentMessage()
        doc_msg.url = self._upload_result["url"]
        doc_msg.mimetype = self._mimetype
        doc_msg.file_name = self._file_name
        doc_msg.file_sha256 = self._file_sha256
        doc_msg.file_length = self._file_length
        doc_msg.media_key = self._media_key
        doc_msg.media_key_timestamp = self._media_key_timestamp
        doc_msg.file_enc_sha256 = self._file_enc_sha256
        
        if self._direct_path:
            doc_msg.direct_path = self._direct_path
        
        if self._caption:
            doc_msg.caption = self._caption
        
        if self._jpeg_thumbnail:
            doc_msg.jpeg_thumbnail = self._jpeg_thumbnail
        
        return doc_msg

