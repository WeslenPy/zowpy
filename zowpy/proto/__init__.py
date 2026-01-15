"""
Protobuf - Sistema de protobuf assíncrono estilo whatsmeow.

Centraliza todas as operações de protobuf de forma assíncrona.
"""

from .messages import (
    AsyncMessageBuilder,
    AsyncMessageParser,
    MessageType,
    TextMessage,
    ImageMessage,
    VideoMessage,
    AudioMessage,
    DocumentMessage,
)
from .handshake import AsyncHandshakeMessageBuilder, AsyncHandshakeMessageParser
from .client_payload import AsyncClientPayloadBuilder
from .helpers import serialize_async, deserialize_async

__all__ = [
    "AsyncMessageBuilder",
    "AsyncMessageParser",
    "MessageType",
    "TextMessage",
    "ImageMessage",
    "VideoMessage",
    "AudioMessage",
    "DocumentMessage",
    "AsyncHandshakeMessageBuilder",
    "AsyncHandshakeMessageParser",
    "AsyncClientPayloadBuilder",
    "serialize_async",
    "deserialize_async",
]

