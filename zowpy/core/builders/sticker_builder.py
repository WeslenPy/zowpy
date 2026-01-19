"""
Sticker Builder - Constrói StickerMessage protobuf para envio de stickers.
"""

import os
import time
import hashlib
import secrets
from typing import Optional
from loguru import logger

from ...utils.media_tools import ImageTools, ImageMetadata
from ...utils.tools import WATools
from ...core.media.media_cipher import MediaCipher
from ...core.media.media_uploader import AsyncMediaUploader
from ...core.media.media_connection import MediaConnection


class StickerBuilder:
    """Constrói StickerMessage protobuf para envio de stickers."""
    
    def __init__(
        self,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection
    ):
        """Inicializa StickerBuilder."""
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
        is_animated: bool = False,
        is_avatar: bool = False,
        is_ai_sticker: bool = False,
        is_lottie: bool = False,
        progress_callback: Optional[callable] = None
    ) -> 'StickerBuilder':
        """Cria StickerBuilder a partir de arquivo."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        # Processa sticker (tratado como imagem)
        image_metadata = ImageTools.process_image(filepath)
        
        builder = cls(media_cipher, media_uploader, media_connection)
        builder._filepath = filepath
        builder._image_metadata = image_metadata
        builder._is_animated = is_animated
        builder._is_avatar = is_avatar
        builder._is_ai_sticker = is_ai_sticker
        builder._is_lottie = is_lottie
        builder._progress_callback = progress_callback
        
        return builder
    
    async def upload_and_build(
        self,
        to_jid: str,
        from_jid: str
    ) -> 'StickerMessage':
        """Faz upload e constrói StickerMessage protobuf completo."""
        if not hasattr(self, '_filepath'):
            raise RuntimeError("StickerBuilder não foi inicializado com filepath")
        
        # 1. Lê arquivo
        with open(self._filepath, 'rb') as f:
            file_data = f.read()
        
        # 2. Gera media_key
        self._media_key = secrets.token_bytes(32)
        self._media_key_timestamp = int(time.time())
        
        # 3. Criptografa sticker
        encrypted_data = self._media_cipher.encrypt_sticker(file_data, self._media_key)
        self._file_enc_sha256 = hashlib.sha256(encrypted_data).digest()
        
        # 4. Obtém media connection
        media_conn = await self._media_connection.get_connection()
        hosts = media_conn["hosts"]
        auth = media_conn["auth"]
        
        # Seleciona primeiro host (como zowsup: getHosts()[0])
        host = hosts[0] if hosts else None
        if not host:
            raise RuntimeError("Nenhum host disponível na media connection")
        
        # Constrói upload URL (stickers usam /mms/image)
        # IMPORTANTE: usa hash dos DADOS CRIPTOGRAFADOS, não dos originais (como zowsup)
        b64Hash = WATools.getDataHashForUpload(encrypted_data)
        b64Hash_urlsafe = b64Hash.replace('+', '-').replace('/', '_').replace('=', '')
        upload_url = f"https://{host}/mms/image/{b64Hash_urlsafe}?auth={auth}&token={b64Hash_urlsafe}"
        
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
        
        # 6. Constrói StickerMessage
        from ...proto.e2e_pb2 import Message
        
        sticker_msg = Message.StickerMessage()
        sticker_msg.url = self._upload_result["url"]
        sticker_msg.mimetype = self._image_metadata.mimetype
        sticker_msg.file_sha256 = self._image_metadata.file_sha256
        sticker_msg.file_enc_sha256 = self._file_enc_sha256
        sticker_msg.media_key = self._media_key
        sticker_msg.media_key_timestamp = self._media_key_timestamp
        sticker_msg.file_length = self._image_metadata.file_length
        sticker_msg.width = self._image_metadata.width
        sticker_msg.height = self._image_metadata.height
        
        if self._direct_path:
            sticker_msg.direct_path = self._direct_path
        
        sticker_msg.is_animated = self._is_animated
        sticker_msg.is_avatar = self._is_avatar
        sticker_msg.is_ai_sticker = self._is_ai_sticker
        sticker_msg.is_lottie = self._is_lottie
        sticker_msg.sticker_sent_ts = int(time.time() * 1000)  # Timestamp em milissegundos
        
        return sticker_msg

