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
    MessageMetaAttributes,
)
from .iq import IqProtocolEntity, GetKeysIqProtocolEntity, SetKeysIqProtocolEntity
from .presence import PresenceProtocolEntity
from .receipt import ReceiptProtocolEntity, RetryOutgoingReceiptProtocolEntity
from .ack import AckProtocolEntity
from .enc import EncProtocolEntity

__all__ = [
    "ProtocolEntity",
    "AuthProtocolEntity",
    "ChallengeProtocolEntity",
    "ResponseProtocolEntity",
    "MessageProtocolEntity",
    "TextMessageProtocolEntity",
    "ExtendedTextMessageProtocolEntity",
    "MessageMetaAttributes",
    "IqProtocolEntity",
    "GetKeysIqProtocolEntity",
    "SetKeysIqProtocolEntity",
    "PresenceProtocolEntity",
    "ReceiptProtocolEntity",
    "RetryOutgoingReceiptProtocolEntity",
    "AckProtocolEntity",
    "EncProtocolEntity",
]

