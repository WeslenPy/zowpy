"""
Attributes - Classes de atributos para mensagens de mídia.

Baseado no padrão do zowsuplib.
"""

from .attributes_media import MediaAttributes, ContextInfoAttributes
from .attributes_downloadablemedia import DownloadableMediaMessageAttributes
from .attributes_image import ImageAttributes
from .attributes_video import VideoAttributes
from .attributes_audio import AudioAttributes
from .attributes_document import DocumentAttributes
from .attributes_sticker import StickerAttributes
from .attributes_message_meta import MessageMetaAttributes
from .attributes_message import MessageAttributes
from .converter import AttributesConverter

__all__ = [
    "MediaAttributes",
    "ContextInfoAttributes",
    "DownloadableMediaMessageAttributes",
    "ImageAttributes",
    "VideoAttributes",
    "AudioAttributes",
    "DocumentAttributes",
    "StickerAttributes",
    "MessageMetaAttributes",
    "MessageAttributes",
    "AttributesConverter",
]

