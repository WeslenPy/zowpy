"""
Media Protocol Entities - Entidades de protocolo para mensagens de mídia.

Baseado no padrão do zowsuplib.
"""

from .message_media import MediaMessageProtocolEntity
from .message_media_downloadable import DownloadableMediaMessageProtocolEntity
from .message_media_downloadable_image import ImageDownloadableMediaMessageProtocolEntity
from .message_media_downloadable_video import VideoDownloadableMediaMessageProtocolEntity
from .message_media_downloadable_audio import AudioDownloadableMediaMessageProtocolEntity
from .message_media_downloadable_document import DocumentDownloadableMediaMessageProtocolEntity
from .message_media_downloadable_sticker import StickerDownloadableMediaMessageProtocolEntity

__all__ = [
    "MediaMessageProtocolEntity",
    "DownloadableMediaMessageProtocolEntity",
    "ImageDownloadableMediaMessageProtocolEntity",
    "VideoDownloadableMediaMessageProtocolEntity",
    "AudioDownloadableMediaMessageProtocolEntity",
    "DocumentDownloadableMediaMessageProtocolEntity",
    "StickerDownloadableMediaMessageProtocolEntity",
]

