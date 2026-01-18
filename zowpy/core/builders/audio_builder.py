"""
Audio Builder - Constrói AudioMessage protobuf para envio de áudio.

Baseado no comportamento do WhatsApp para envio de áudio/PTT.
"""

import os
import time
import hashlib
import secrets
import random
from typing import Optional, Dict, Any
from loguru import logger

from ...utils.media_tools import AudioTools, AudioMetadata, normalize_file_path_or_url
from ...core.media.media_cipher import MediaCipher
from ...core.media.media_uploader import AsyncMediaUploader
from ...core.media.media_connection import MediaConnection


class AudioBuilder:
    """
    Constrói AudioMessage protobuf para envio de áudio.
    
    Suporta áudio normal e PTT (push-to-talk/voice message).
    """
    
    def __init__(
        self,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection
    ):
        """Inicializa AudioBuilder."""
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
        ptt: bool = False,
        progress_callback: Optional[callable] = None
    ) -> 'AudioBuilder':
        """Cria AudioBuilder a partir de arquivo ou URL."""
        # Normaliza: se for URL, baixa temporariamente
        filepath, is_temporary = await normalize_file_path_or_url(
            file_path_or_url,
            default_extension=".mp3",
            prefix="audio"
        )
        
        # Processa áudio
        mimetype = AudioTools.get_mimetype(filepath)
        duration = AudioTools.get_duration(filepath)
        
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        file_length = len(file_data)
        file_sha256 = hashlib.sha256(file_data).digest()
        
        # Gera waveform se PTT
        waveform = None
        if ptt:
            waveform = AudioTools.generate_waveform(filepath, duration)
        
        try:
            builder = cls(media_cipher, media_uploader, media_connection)
            builder._filepath = filepath
            builder._is_temporary = is_temporary
            builder._mimetype = mimetype
            builder._duration = duration
            builder._file_length = file_length
            builder._file_sha256 = file_sha256
            builder._ptt = ptt
            builder._waveform = waveform
            builder._progress_callback = progress_callback
            
            return builder
        except Exception as e:
            # Limpa arquivo temporário em caso de erro
            if is_temporary:
                try:
                    os.unlink(filepath)
                except:
                    pass
            raise
    
    async def upload_and_build(
        self,
        to_jid: str,
        from_jid: str
    ) -> 'AudioMessage':
        """Faz upload e constrói AudioMessage protobuf completo."""
        if not hasattr(self, '_filepath'):
            raise RuntimeError("AudioBuilder não foi inicializado com filepath")
        
        # 1. Lê arquivo
        with open(self._filepath, 'rb') as f:
            file_data = f.read()
        
        # 2. Gera media_key
        self._media_key = secrets.token_bytes(32)
        self._media_key_timestamp = int(time.time())
        
        # 3. Criptografa áudio
        encrypted_data = self._media_cipher.encrypt_audio(file_data, self._media_key)
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
        media_type = "ptt" if self._ptt else "audio"
        upload_url = f"https://{host}/mms/{media_type}/{file_hash_base64}?auth={auth}&token={file_hash_base64}"
        
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
        
        # 6. Constrói AudioMessage
        from ...proto.e2e_pb2 import AudioMessage
        
        audio_msg = AudioMessage()
        audio_msg.url = self._upload_result["url"]
        audio_msg.mimetype = self._mimetype
        audio_msg.file_sha256 = self._file_sha256
        audio_msg.file_length = self._file_length
        audio_msg.seconds = self._duration
        audio_msg.ptt = self._ptt
        audio_msg.media_key = self._media_key
        audio_msg.media_key_timestamp = self._media_key_timestamp
        audio_msg.file_enc_sha256 = self._file_enc_sha256
        
        if self._direct_path:
            audio_msg.direct_path = self._direct_path
        
        if self._ptt and self._waveform:
            audio_msg.waveform = self._waveform
        
        # Remove arquivo temporário se foi baixado de URL
        if hasattr(self, '_is_temporary') and self._is_temporary:
            try:
                os.unlink(self._filepath)
                logger.debug(f"Arquivo temporário removido: {self._filepath}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
        
        return audio_msg

