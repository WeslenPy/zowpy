"""
Image Builder - Constrói ImageMessage protobuf para envio de imagens.

Baseado no comportamento do WhatsApp para envio de imagens.
"""

import os
import time
import hashlib
from typing import Optional, Dict, Any
from loguru import logger

from ...utils.media_tools import ImageTools, ImageMetadata, VideoMetadata, normalize_file_path_or_url,VideoTools
from ...utils.tools import WATools
from ...core.media.media_cipher import MediaCipher
from ...core.media.media_uploader import AsyncMediaUploader
from ...core.media.media_connection import MediaConnection


class VideoBuilder:
    """
    Constrói VideoBuilder protobuf para envio de imagens.
    
    Fluxo completo:
    1. Processa video (dimensões, thumbnail, SHA256)
    2. Obtém media connection
    3. Gera media_key e criptografa video
    4. Faz upload HTTP
    5. Constrói VideoMessage protobuf
    """

    _video_metadata:VideoMetadata 
    
    def __init__(
        self,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection
    ):
        """
        Inicializa ImageBuilder.
        
        Args:
            media_cipher: MediaCipher para criptografar imagem
            media_uploader: AsyncMediaUploader para upload HTTP
            media_connection: MediaConnection para obter conexão de mídia
        """
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
        caption: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> 'VideoBuilder':
        """
        Cria VideoBuilder a partir de arquivo no filesystem ou URL.
        
        Args:
            file_path_or_url: Caminho do arquivo de imagem ou URL
            media_cipher: MediaCipher para criptografia
            media_uploader: AsyncMediaUploader para upload
            media_connection: MediaConnection para obter conexão
            caption: Legenda da imagem (opcional)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            VideoBuilder: Builder pronto para build_protobuf()
        """
        filepath = None
        is_temporary = False
        try:
            filepath, is_temporary = await normalize_file_path_or_url(
                file_path_or_url,
                default_extension=".mp4",
                prefix="video"
            )
            video_metadata = VideoTools.process_video(filepath)
            builder = cls(media_cipher, media_uploader, media_connection)
            builder._filepath = filepath
            builder._is_temporary = is_temporary
            builder._video_metadata:VideoMetadata = video_metadata
            builder._caption = caption
            builder._progress_callback = progress_callback
            return builder
        except Exception as e:
            logger.exception("Erro em media_tools ao processar imagem (ImageBuilder.from_filepath): %s", e)
            if is_temporary and filepath:
                try:
                    os.unlink(filepath)
                except Exception:
                    pass
            raise
    
    @classmethod
    async def from_url(
        cls,
        url: str,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection,
        caption: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> 'VideoBuilder':
        """
        Cria VideoBuilder a partir de URL (baixa temporariamente).
        
        Nota: Baixa arquivo temporariamente, processa, e então constrói.
        
        Args:
            url: URL da imagem
            media_cipher: MediaCipher para criptografia
            media_uploader: AsyncMediaUploader para upload
            media_connection: MediaConnection para obter conexão
            caption: Legenda da imagem (opcional)
            progress_callback: Callback para progresso (opcional)
        
        Returns:
            VideoBuilder: Builder pronto para build_protobuf()
        """
        # TODO: Implementar download de URL
        # Por enquanto levanta NotImplementedError
        raise NotImplementedError("from_url() ainda não implementado")
    
    async def build_protobuf(
        self,
        to_jid: str,
        from_jid: str
    ) -> 'VideoMessage':
        """
        Constrói ImageMessage protobuf (requer upload prévio).
        
        Nota: Este método assume que upload já foi feito.
        Use upload_and_build() para fluxo completo.
        
        Args:
            to_jid: JID do destinatário
            from_jid: JID do remetente
        
        Returns:
            ImageMessage: Protobuf pronto para envio
        """
        if not hasattr(self, '_video_metadata'):
            raise RuntimeError("VideoBuilder não foi inicializado corretamente")
        
        if not hasattr(self, '_upload_result'):
            raise RuntimeError("Upload ainda não foi feito. Use upload_and_build()")
        
        from ...proto.e2e_pb2 import Message
        
        video_msg = Message.VideoMessage()
        
        # Campos obrigatórios
        video_msg.url = self._upload_result["url"]
        video_msg.mimetype = self._video_metadata.mimetype
        video_msg.file_sha256 = self._video_metadata.file_sha256
        video_msg.file_length = self._video_metadata.file_length
        video_msg.width = self._video_metadata.width
        video_msg.height = self._video_metadata.height
        video_msg.seconds = self._video_metadata.seconds
        video_msg.gif_playback =   self._video_metadata.gif_playback
        
        # Campos opcionais
        if self._caption:
            video_msg.caption = self._caption
        
        if self._video_metadata.jpeg_thumbnail:
            video_msg.jpeg_thumbnail = self._video_metadata.jpeg_thumbnail
        
        if hasattr(self, '_media_key'):
            video_msg.media_key = self._media_key
            video_msg.media_key_timestamp = self._media_key_timestamp
        
        if hasattr(self, '_file_enc_sha256'):
            video_msg.file_enc_sha256 = self._file_enc_sha256
        
        if hasattr(self, '_direct_path') and self._direct_path:
            video_msg.direct_path = self._direct_path


        logger.debug(f"VideoMessage: {video_msg}")
        return video_msg

    
    async def upload_and_build(
        self,
        to_jid: str,
        from_jid: str
    ) -> 'VideoMessage':
        """
        Faz upload e constrói VideoMessage protobuf completo.
        
        Fluxo completo:
        1. Lê arquivo e calcula SHA256
        2. Gera media_key (32 bytes aleatórios)
        3. Criptografa imagem usando MediaCipher
        4. Obtém media connection
        5. Faz upload HTTP
        6. Constrói ImageMessage protobuf
        
        Args:
            to_jid: JID do destinatário
            from_jid: JID do remetente
        
        Returns:
            ImageMessage: Protobuf pronto para envio
        """
        if not hasattr(self, '_filepath'):
            raise RuntimeError("ImageBuilder não foi inicializado com filepath")
        
        # 1. Lê arquivo
        with open(self._filepath, 'rb') as f:
            file_data = f.read()
        
        # 2. Gera media_key (formato compatível com zowsuplib)
        self._media_key = WATools.generate_media_key()
        self._media_key_timestamp = int(time.time())
        
        # 3. Criptografa imagem
        encrypted_data = self._media_cipher.encrypt_video(file_data, self._media_key)
        self._file_enc_sha256 = hashlib.sha256(encrypted_data).digest()
        
        logger.debug(
            f"Criptografando imagem: original={len(file_data)} bytes, "
            f"encrypted={len(encrypted_data)} bytes"
        )
        
        # 4. Obtém media connection
        media_conn = await self._media_connection.get_connection()
        hosts = media_conn["hosts"]
        auth = media_conn["auth"]
        
        # Seleciona primeiro host (como zowsup: getHosts()[0])
        host = hosts[0] if hosts else None
        if not host:
            raise RuntimeError("Nenhum host disponível na media connection")
        
        # Constrói upload URL (formato novo: https://{host}/mms/image/{hash}?auth={auth}&token={hash})
        # IMPORTANTE: usa hash dos DADOS CRIPTOGRAFADOS, não dos originais (como zowsup)
        b64Hash = WATools.getDataHashForUpload(encrypted_data)
        b64Hash_urlsafe = b64Hash.replace('+', '-').replace('/', '_').replace('=', '')
        upload_url = f"https://{host}/mms/video/{b64Hash_urlsafe}?auth={auth}&token={b64Hash_urlsafe}"
        
        logger.debug(f"Upload URL: {upload_url}")
        # 5. Faz upload
        logger.debug(f"Iniciando upload de imagem para {upload_url[:50]}...")
        
        # Cria arquivo temporário com dados criptografados
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(encrypted_data)
            tmp_encrypted_path = tmp_file.name


        logger.debug(f"Upload URL: {upload_url[:80]}...")
        
        try:
            upload_result = await self._media_uploader.upload(
                filepath=tmp_encrypted_path,
                upload_url=upload_url,
                progress_callback=self._progress_callback
            )
            self._upload_result = upload_result
            self._direct_path = upload_result.get("direct_path", "")

            logger.debug(f"Upload result: {upload_result}")
        finally:
            # Remove arquivo temporário
            try:
                os.unlink(tmp_encrypted_path)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário {tmp_encrypted_path}: {e}")
        
        # Limpa arquivo temporário se foi baixado de URL
        if hasattr(self, '_is_temporary') and self._is_temporary:
            try:
                os.unlink(self._filepath)
                logger.debug(f"Arquivo temporário removido: {self._filepath}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
        
        # 6. Constrói ImageMessage
        return await self.build_protobuf(to_jid, from_jid)

