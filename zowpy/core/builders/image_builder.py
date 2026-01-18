"""
Image Builder - Constrói ImageMessage protobuf para envio de imagens.

Baseado no comportamento do WhatsApp para envio de imagens.
"""

import os
import time
import hashlib
from typing import Optional, Dict, Any
from loguru import logger

from ...utils.media_tools import ImageTools, ImageMetadata, normalize_file_path_or_url
from ...core.media.media_cipher import MediaCipher
from ...core.media.media_uploader import AsyncMediaUploader
from ...core.media.media_connection import MediaConnection


class ImageBuilder:
    """
    Constrói ImageMessage protobuf para envio de imagens.
    
    Fluxo completo:
    1. Processa imagem (dimensões, thumbnail, SHA256)
    2. Obtém media connection
    3. Gera media_key e criptografa imagem
    4. Faz upload HTTP
    5. Constrói ImageMessage protobuf
    """
    
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
    ) -> 'ImageBuilder':
        """
        Cria ImageBuilder a partir de arquivo no filesystem ou URL.
        
        Args:
            file_path_or_url: Caminho do arquivo de imagem ou URL
            media_cipher: MediaCipher para criptografia
            media_uploader: AsyncMediaUploader para upload
            media_connection: MediaConnection para obter conexão
            caption: Legenda da imagem (opcional)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ImageBuilder: Builder pronto para build_protobuf()
        """
        # Normaliza: se for URL, baixa temporariamente
        filepath, is_temporary = await normalize_file_path_or_url(
            file_path_or_url,
            default_extension=".jpg",
            prefix="image"
        )
        
        try:
            # Processa imagem
            image_metadata = ImageTools.process_image(filepath)
            
            # Cria builder
            builder = cls(media_cipher, media_uploader, media_connection)
            builder._filepath = filepath
            builder._is_temporary = is_temporary
            builder._image_metadata = image_metadata
            builder._caption = caption
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
    
    @classmethod
    async def from_url(
        cls,
        url: str,
        media_cipher: MediaCipher,
        media_uploader: AsyncMediaUploader,
        media_connection: MediaConnection,
        caption: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> 'ImageBuilder':
        """
        Cria ImageBuilder a partir de URL (baixa temporariamente).
        
        Nota: Baixa arquivo temporariamente, processa, e então constrói.
        
        Args:
            url: URL da imagem
            media_cipher: MediaCipher para criptografia
            media_uploader: AsyncMediaUploader para upload
            media_connection: MediaConnection para obter conexão
            caption: Legenda da imagem (opcional)
            progress_callback: Callback para progresso (opcional)
        
        Returns:
            ImageBuilder: Builder pronto para build_protobuf()
        """
        # TODO: Implementar download de URL
        # Por enquanto levanta NotImplementedError
        raise NotImplementedError("from_url() ainda não implementado")
    
    async def build_protobuf(
        self,
        to_jid: str,
        from_jid: str
    ) -> 'ImageMessage':
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
        if not hasattr(self, '_image_metadata'):
            raise RuntimeError("ImageBuilder não foi inicializado corretamente")
        
        if not hasattr(self, '_upload_result'):
            raise RuntimeError("Upload ainda não foi feito. Use upload_and_build()")
        
        from ...proto.e2e_pb2 import ImageMessage
        
        image_msg = ImageMessage()
        
        # Campos obrigatórios
        image_msg.url = self._upload_result["url"]
        image_msg.mimetype = self._image_metadata.mimetype
        image_msg.file_sha256 = self._image_metadata.file_sha256
        image_msg.file_length = self._image_metadata.file_length
        image_msg.width = self._image_metadata.width
        image_msg.height = self._image_metadata.height
        
        # Campos opcionais
        if self._caption:
            image_msg.caption = self._caption
        
        if self._image_metadata.jpeg_thumbnail:
            image_msg.jpeg_thumbnail = self._image_metadata.jpeg_thumbnail
        
        if hasattr(self, '_media_key'):
            image_msg.media_key = self._media_key
            image_msg.media_key_timestamp = self._media_key_timestamp
        
        if hasattr(self, '_file_enc_sha256'):
            image_msg.file_enc_sha256 = self._file_enc_sha256
        
        if hasattr(self, '_direct_path') and self._direct_path:
            image_msg.direct_path = self._direct_path
        
        return image_msg
    
    async def upload_and_build(
        self,
        to_jid: str,
        from_jid: str
    ) -> 'ImageMessage':
        """
        Faz upload e constrói ImageMessage protobuf completo.
        
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
        
        # 2. Gera media_key (32 bytes aleatórios)
        import secrets
        self._media_key = secrets.token_bytes(32)
        self._media_key_timestamp = int(time.time())
        
        # 3. Criptografa imagem
        encrypted_data = self._media_cipher.encrypt_image(file_data, self._media_key)
        self._file_enc_sha256 = hashlib.sha256(encrypted_data).digest()
        
        logger.debug(
            f"Criptografando imagem: original={len(file_data)} bytes, "
            f"encrypted={len(encrypted_data)} bytes"
        )
        
        # 4. Obtém media connection
        media_conn = await self._media_connection.get_connection()
        hosts = media_conn["hosts"]
        auth = media_conn["auth"]
        
        # Seleciona host aleatoriamente
        import random
        host = random.choice(hosts) if hosts else None
        if not host:
            raise RuntimeError("Nenhum host disponível na media connection")
        
        # Constrói upload URL (formato novo: https://{host}/mms/image/{hash}?auth={auth}&token={hash})
        file_hash_base64 = hashlib.sha256(file_data).hexdigest()[:32]
        upload_url = f"https://{host}/mms/image/{file_hash_base64}?auth={auth}&token={file_hash_base64}"
        
        # 5. Faz upload
        logger.debug(f"Iniciando upload de imagem para {upload_url[:50]}...")
        
        # Cria arquivo temporário com dados criptografados
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
            # Remove arquivo temporário
            try:
                os.unlink(tmp_encrypted_path)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário {tmp_encrypted_path}: {e}")
        
        # 6. Constrói ImageMessage
        return await self.build_protobuf(to_jid, from_jid)

