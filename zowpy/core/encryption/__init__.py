"""
Encryption Layer - Camada de criptografia E2E para mensagens.

Descriptografa mensagens recebidas e criptografa mensagens para envio.
"""

from .receiver import EncryptionReceiver
from .sender import EncryptionSender

__all__ = [
    "EncryptionReceiver",
    "EncryptionSender",
]

