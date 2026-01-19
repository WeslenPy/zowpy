"""
Media Tools - Ferramentas para processar mídia, gerar thumbnails e extrair metadados.

Suporte para:
- ImageTools: dimensões, thumbnail JPEG (Pillow)
- VideoTools: duração, propriedades (opcional: opencv-python/ffmpeg-python)
- AudioTools: duração, waveform (opcional: pydub/mutagen)
- MIME type detection
"""

import hashlib
import os
import mimetypes
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urlparse
from loguru import logger

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

# Pillow para processamento de imagens
try:
    from PIL import Image, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    logger.warning("Pillow não instalado. Processamento de imagens limitado.")

# pydub para processamento de áudio
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    logger.debug("pydub não instalado. Waveform generation será limitado.")

# mutagen para metadados de áudio
try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    logger.debug("mutagen não instalado. Metadados de áudio limitados.")


async def normalize_file_path_or_url(file_path_or_url: str, default_extension: Optional[str] = None, prefix: str = "download") -> Tuple[str, bool]:
    """
    Normaliza file_path_or_url: se for URL, baixa temporariamente.
    
    Args:
        file_path_or_url: Caminho de arquivo local ou URL
        default_extension: Extensão padrão se não conseguir detectar da URL
        prefix: Prefixo para nome do arquivo baixado
    
    Returns:
        tuple: (filepath, is_temporary) - Caminho do arquivo e se é temporário
    """
    # Verifica se é URL (começa com http:// ou https://)
    if file_path_or_url.startswith(("http://", "https://")):
        logger.debug(f"Detectada URL, baixando arquivo: {file_path_or_url[:50]}...")
        
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp é necessário para baixar arquivos de URL")
        
        # Faz download assíncrono
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(file_path_or_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    response.raise_for_status()
                    
                    # Extrai filename da URL
                    parsed_url = urlparse(file_path_or_url)
                    url_path = parsed_url.path
                    filename = os.path.basename(url_path) if url_path else None
                    
                    # Gera filename se não conseguiu extrair
                    if not filename or len(filename) == 0 or len(filename) > 200:
                        url_hash = hashlib.sha256(file_path_or_url.encode('utf-8')).hexdigest()[:32]
                        ext = default_extension or ".tmp"
                        filename = f"{prefix}_{url_hash}{ext}"
                    else:
                        # Sanitiza filename
                        invalid_chars = '<>:"|?*\\'
                        for char in invalid_chars:
                            filename = filename.replace(char, '_')
                        
                        if len(filename) > 200:
                            name, ext = os.path.splitext(filename)
                            filename = name[:190] + (ext or default_extension or "")
                        
                        if default_extension and not os.path.splitext(filename)[1]:
                            filename += default_extension
                    
                    # Cria diretório temporário
                    download_dir = Path(tempfile.gettempdir()) / "zowpy_downloads"
                    download_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Monta caminho completo
                    filepath = download_dir / filename
                    
                    # Evita conflitos de nome
                    counter = 1
                    original_filepath = filepath
                    while filepath.exists():
                        name, ext = os.path.splitext(original_filepath)
                        filepath = Path(f"{name}_{counter}{ext}")
                        counter += 1
                        if counter > 1000:
                            raise Exception("Muitos arquivos com o mesmo nome no diretório")
                    
                    # Salva arquivo
                    filepath_str = str(filepath)
                    if HAS_AIOFILES:
                        async with aiofiles.open(filepath_str, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                    else:
                        # Fallback síncrono se aiofiles não estiver disponível
                        with open(filepath_str, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                    
                    logger.debug(f"Arquivo baixado de URL e salvo em: {filepath_str}")
                    return (filepath_str, True)
                    
            except aiohttp.ClientError as e:
                logger.error(f"Erro ao baixar arquivo da URL {file_path_or_url}: {e}")
                raise Exception(f"Erro ao baixar arquivo: {str(e)}") from e
    else:
        # É caminho de arquivo local
        if not os.path.exists(file_path_or_url):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path_or_url}")
        
        return (file_path_or_url, False)


# Importa aiofiles se disponível
try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False
    if HAS_AIOHTTP:
        logger.warning("aiofiles não instalado. Download de URLs será mais lento (usa modo síncrono).")


@dataclass
class ImageMetadata:
    """Metadados de imagem."""
    width: int
    height: int
    mimetype: str
    file_length: int
    file_sha256: bytes
    jpeg_thumbnail: Optional[bytes] = None


@dataclass
class VideoMetadata:
    """Metadados de vídeo."""
    width: int
    height: int
    duration_seconds: int
    mimetype: str
    file_length: int
    file_sha256: bytes
    jpeg_thumbnail: Optional[bytes] = None
    is_gif: bool = False


@dataclass
class AudioMetadata:
    """Metadados de áudio."""
    duration_seconds: int
    mimetype: str
    file_length: int
    file_sha256: bytes
    waveform: Optional[bytes] = None
    is_ptt: bool = False


@dataclass
class DocumentMetadata:
    """Metadados de documento."""
    mimetype: str
    file_name: str
    file_length: int
    file_sha256: bytes
    page_count: Optional[int] = None
    jpeg_thumbnail: Optional[bytes] = None


class ImageTools:
    """Ferramentas para processar imagens."""
    
    MAX_THUMBNAIL_SIZE = 32 * 1024  # 32KB máximo
    MAX_THUMBNAIL_DIMENSION = 64  # 64px máximo (igual zowsuplib PREVIEW_WIDTH/HEIGHT)
    JPEG_QUALITY = 85
    
    @staticmethod
    def get_mimetype(filepath: str) -> str:
        """
        Detecta MIME type de imagem.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            str: MIME type (ex: "image/jpeg", "image/png")
        """
        mimetype, _ = mimetypes.guess_type(filepath)
        if not mimetype or not mimetype.startswith("image/"):
            # Fallback baseado em extensão
            ext = os.path.splitext(filepath)[1].lower()
            ext_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mimetype = ext_map.get(ext, "image/jpeg")
        return mimetype
    
    @staticmethod
    def get_dimensions(filepath: str) -> Tuple[int, int]:
        """
        Obtém dimensões da imagem.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            tuple: (width, height)
        
        Raises:
            RuntimeError: Se Pillow não estiver instalado
            FileNotFoundError: Se arquivo não existir
        """
        if not HAS_PILLOW:
            raise RuntimeError("Pillow é necessário para obter dimensões de imagem")
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        try:
            with Image.open(filepath) as img:
                return img.size  # (width, height)
        except Exception as e:
            raise RuntimeError(f"Erro ao obter dimensões de {filepath}: {e}")
    
    @staticmethod
    def generate_thumbnail(
        filepath: str,
        max_dimension: int = MAX_THUMBNAIL_DIMENSION,
        quality: int = JPEG_QUALITY,
        max_size: int = MAX_THUMBNAIL_SIZE
    ) -> bytes:
        """
        Gera thumbnail JPEG da imagem.
        
        Baseado em zowsuplib ImageTools.generatePreviewFromImage():
        - Usa PREVIEW_WIDTH = 64 e PREVIEW_HEIGHT = 64
        - Redimensiona mantendo proporção (thumbnail limita ambas dimensões)
        - Máximo 64px em ambas dimensões (igual zowsuplib)
        - Máximo 32KB de tamanho
        - Formato JPEG
        
        Args:
            filepath: Caminho do arquivo
            max_dimension: Dimensão máxima (padrão: 64px, igual zowsuplib)
            quality: Qualidade JPEG 1-100 (padrão: 85)
            max_size: Tamanho máximo em bytes (padrão: 32KB)
        
        Returns:
            bytes: Thumbnail JPEG
        
        Raises:
            RuntimeError: Se Pillow não estiver instalado
        """
        if not HAS_PILLOW:
            raise RuntimeError("Pillow é necessário para gerar thumbnail")
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        try:
            with Image.open(filepath) as img:
                # Converte para RGB se necessário (para PNG com transparência, etc)
                if img.mode in ("RGBA", "LA", "P"):
                    # Cria fundo branco para imagens com transparência
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Redimensiona usando thumbnail (igual zowsuplib scaleImage)
                # thumbnail() mantém proporção e limita ambas dimensões ao máximo
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
                # Gera JPEG e ajusta qualidade se necessário
                import io
                thumbnail_bytes = io.BytesIO()
                
                # Tenta qualidade inicial
                img.save(thumbnail_bytes, format="JPEG", quality=quality, optimize=True)
                thumbnail_data = thumbnail_bytes.getvalue()
                
                # Reduz qualidade se exceder tamanho máximo
                current_quality = quality
                while len(thumbnail_data) > max_size and current_quality > 10:
                    current_quality -= 10
                    thumbnail_bytes = io.BytesIO()
                    img.save(thumbnail_bytes, format="JPEG", quality=current_quality, optimize=True)
                    thumbnail_data = thumbnail_bytes.getvalue()
                
                if len(thumbnail_data) > max_size:
                    logger.warning(
                        f"Thumbnail ainda excede {max_size} bytes após reduzir qualidade. "
                        f"Tamanho: {len(thumbnail_data)} bytes"
                    )
                
                return thumbnail_data
                
        except Exception as e:
            raise RuntimeError(f"Erro ao gerar thumbnail de {filepath}: {e}")
    
    @staticmethod
    def process_image(filepath: str) -> ImageMetadata:
        """
        Processa imagem completa: dimensões, SHA256, thumbnail.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            ImageMetadata: Metadados da imagem
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        # Obtém dimensões
        width, height = ImageTools.get_dimensions(filepath) if HAS_PILLOW else (0, 0)
        
        # Obtém MIME type
        mimetype = ImageTools.get_mimetype(filepath)
        
        # Lê arquivo e calcula SHA256
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        file_length = len(file_data)
        sha256 = hashlib.sha256(file_data).digest()  # Bytes raw (32 bytes) - protobuf espera bytes, não base64
        
        # Gera thumbnail
        jpeg_thumbnail = None
        try:
            jpeg_thumbnail = ImageTools.generate_thumbnail(filepath) if HAS_PILLOW else None
        except Exception as e:
            logger.warning(f"Erro ao gerar thumbnail para {filepath}: {e}")
        
        return ImageMetadata(
            width=width,
            height=height,
            mimetype=mimetype,
            file_length=file_length,
            file_sha256=sha256,
            jpeg_thumbnail=jpeg_thumbnail
        )


class VideoTools:
    """Ferramentas para processar vídeos."""
    
    MAX_THUMBNAIL_SIZE = 32 * 1024  # 32KB máximo
    MAX_THUMBNAIL_DIMENSION = 640  # 640px máximo
    JPEG_QUALITY = 85
    
    @staticmethod
    def get_mimetype(filepath: str) -> str:
        """Detecta MIME type de vídeo."""
        mimetype, _ = mimetypes.guess_type(filepath)
        if not mimetype or not mimetype.startswith("video/"):
            ext = os.path.splitext(filepath)[1].lower()
            ext_map = {
                ".mp4": "video/mp4",
                ".avi": "video/x-msvideo",
                ".mov": "video/quicktime",
                ".webm": "video/webm",
            }
            mimetype = ext_map.get(ext, "video/mp4")
        return mimetype
    
    @staticmethod
    def get_duration(filepath: str) -> int:
        """
        Obtém duração do vídeo em segundos.
        
        Nota: Requer biblioteca externa (opencv-python ou ffmpeg-python).
        Por enquanto retorna 0 se não disponível.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            int: Duração em segundos (0 se não disponível)
        """
        # TODO: Implementar usando opencv-python ou ffmpeg-python
        # Por enquanto retorna 0
        logger.debug(f"Duração de vídeo não implementada ainda para {filepath}")
        return 0
    
    @staticmethod
    def get_dimensions(filepath: str) -> Tuple[int, int]:
        """
        Obtém dimensões do vídeo.
        
        Nota: Requer biblioteca externa.
        Por enquanto retorna (0, 0) se não disponível.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            tuple: (width, height) ou (0, 0) se não disponível
        """
        # TODO: Implementar usando opencv-python ou ffmpeg-python
        logger.debug(f"Dimensões de vídeo não implementadas ainda para {filepath}")
        return (0, 0)
    
    @staticmethod
    def is_gif(filepath: str) -> bool:
        """Verifica se arquivo é GIF."""
        mimetype = VideoTools.get_mimetype(filepath)
        return mimetype == "image/gif"
    
    @staticmethod
    def generate_thumbnail(filepath: str) -> bytes:
        """
        Gera thumbnail JPEG do vídeo (primeiro frame).
        
        Nota: Requer biblioteca externa para extrair frame.
        Por enquanto retorna bytes vazios.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            bytes: Thumbnail JPEG (vazio se não disponível)
        """
        # TODO: Implementar usando opencv-python ou ffmpeg-python
        logger.debug(f"Thumbnail de vídeo não implementado ainda para {filepath}")
        return b""


class AudioTools:
    """Ferramentas para processar áudio."""
    
    WAVEFORM_LENGTH = 100  # 100 bytes de waveform (padrão WhatsApp)
    
    @staticmethod
    def get_mimetype(filepath: str) -> str:
        """Detecta MIME type de áudio."""
        mimetype, _ = mimetypes.guess_type(filepath)
        if not mimetype or not mimetype.startswith("audio/"):
            ext = os.path.splitext(filepath)[1].lower()
            ext_map = {
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".ogg": "audio/ogg",
                ".opus": "audio/opus",
                ".wav": "audio/wav",
            }
            mimetype = ext_map.get(ext, "audio/mpeg")
        return mimetype
    
    @staticmethod
    def get_duration(filepath: str) -> int:
        """
        Obtém duração do áudio em segundos.
        
        Usa mutagen ou pydub se disponível.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            int: Duração em segundos (0 se não disponível)
        """
        # Tenta com mutagen primeiro
        if HAS_MUTAGEN:
            try:
                audio_file = MutagenFile(filepath)
                if audio_file is not None:
                    duration = audio_file.info.length
                    return int(duration) if duration else 0
            except Exception as e:
                logger.debug(f"Erro ao obter duração com mutagen para {filepath}: {e}")
        
        # Tenta com pydub
        if HAS_PYDUB:
            try:
                audio = AudioSegment.from_file(filepath)
                return int(len(audio) / 1000)  # Converte ms para segundos
            except Exception as e:
                logger.debug(f"Erro ao obter duração com pydub para {filepath}: {e}")
        
        logger.debug(f"Duração de áudio não disponível para {filepath}")
        return 0
    
    @staticmethod
    def generate_waveform(filepath: Optional[str] = None, duration_seconds: Optional[int] = None) -> bytes:
        """
        Gera waveform aleatório para PTT (push-to-talk).
        
        WhatsApp requer 100 bytes de waveform para PTT.
        Por enquanto gera bytes aleatórios (TODO: gerar baseado em áudio real).
        
        Args:
            filepath: Caminho do arquivo (opcional, não usado ainda)
            duration_seconds: Duração em segundos (opcional)
        
        Returns:
            bytes: Waveform (100 bytes)
        """
        import random
        # Por enquanto gera waveform aleatório
        # TODO: Gerar baseado em áudio real usando pydub
        waveform = bytes([random.randint(0, 255) for _ in range(AudioTools.WAVEFORM_LENGTH)])
        return waveform


class MimeTools:
    """Ferramentas para detectar MIME types."""
    
    @staticmethod
    def get_mime(filepath: str) -> str:
        """
        Detecta MIME type de arquivo.
        
        Args:
            filepath: Caminho do arquivo
        
        Returns:
            str: MIME type
        """
        mimetype, _ = mimetypes.guess_type(filepath)
        if not mimetype:
            ext = os.path.splitext(filepath)[1].lower()
            # Mapeamento comum
            ext_map = {
                ".txt": "text/plain",
                ".pdf": "application/pdf",
                ".zip": "application/zip",
                ".doc": "application/msword",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".xls": "application/vnd.ms-excel",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            mimetype = ext_map.get(ext, "application/octet-stream")
        return mimetype
