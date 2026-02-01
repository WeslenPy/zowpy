"""
Protocol Entities - Classes que herdam de ProtocolNode para abstrair construção de nodes.

Baseado no padrão do zowsuplib, mas usando herança direta de ProtocolNode.
"""

from .base import ProtocolEntity
from .auth import AuthProtocolEntity, ChallengeProtocolEntity, ResponseProtocolEntity
from .message import (
    MessageProtocolEntity,
    TextMessageProtocolEntity,
    ExtendedTextMessageProtocolEntity,
    ProtomessageProtocolEntity,
    MessageMetaAttributes as MessageMetaAttributesSimple,
)
from .iq import IqProtocolEntity, GetKeysIqProtocolEntity, SetKeysIqProtocolEntity
from .iq_push import PushIqProtocolEntity
from .iq_props import PropsIqProtocolEntity
from .iq_trust_contact import TrustContactIqProtocolEntity
from .iq_wmex import WmexQueryIqProtocolEntity, WmexResultIqProtocolEntity
from .ib import IbProtocolEntity, EdgeRoutingIbProtocolEntity
from .presence import PresenceProtocolEntity
from .chatstate import ChatstateProtocolEntity, OutgoingChatstateProtocolEntity
from .receipt import ReceiptProtocolEntity, RetryOutgoingReceiptProtocolEntity
from .ack import AckProtocolEntity
from .enc import EncProtocolEntity

# Importa classes de mídia
from .media import (
    MediaMessageProtocolEntity,
    DownloadableMediaMessageProtocolEntity,
    ImageDownloadableMediaMessageProtocolEntity,
    VideoDownloadableMediaMessageProtocolEntity,
    AudioDownloadableMediaMessageProtocolEntity,
    DocumentDownloadableMediaMessageProtocolEntity,
    StickerDownloadableMediaMessageProtocolEntity,
)

# Importa classes de attributes
from .attributes import (
    MediaAttributes,
    ContextInfoAttributes,
    DownloadableMediaMessageAttributes,
    ImageAttributes,
    VideoAttributes,
    AudioAttributes,
    DocumentAttributes,
    StickerAttributes,
    MessageMetaAttributes,  # A versão completa de attributes
    MessageAttributes,
    AttributesConverter,
)

__all__ = [
    "ProtocolEntity",
    "AuthProtocolEntity",
    "ChallengeProtocolEntity",
    "ResponseProtocolEntity",
    "MessageProtocolEntity",
    "TextMessageProtocolEntity",
    "ExtendedTextMessageProtocolEntity",
    "ProtomessageProtocolEntity",
    "MessageMetaAttributesSimple",  # Versão simples de message.py
    "IqProtocolEntity",
    "GetKeysIqProtocolEntity",
    "SetKeysIqProtocolEntity",
    "PushIqProtocolEntity",
    "PropsIqProtocolEntity",
    "TrustContactIqProtocolEntity",
    "WmexQueryIqProtocolEntity",
    "WmexResultIqProtocolEntity",
    "IbProtocolEntity",
    "EdgeRoutingIbProtocolEntity",
    "PresenceProtocolEntity",
    "ChatstateProtocolEntity",
    "OutgoingChatstateProtocolEntity",
    "ReceiptProtocolEntity",
    "RetryOutgoingReceiptProtocolEntity",
    "AckProtocolEntity",
    "EncProtocolEntity",
    # Media Protocol Entities
    "MediaMessageProtocolEntity",
    "DownloadableMediaMessageProtocolEntity",
    "ImageDownloadableMediaMessageProtocolEntity",
    "VideoDownloadableMediaMessageProtocolEntity",
    "AudioDownloadableMediaMessageProtocolEntity",
    "DocumentDownloadableMediaMessageProtocolEntity",
    "StickerDownloadableMediaMessageProtocolEntity",
    # Attributes
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

