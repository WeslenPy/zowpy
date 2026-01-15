# -*- coding: utf-8 -*-
"""
Axolotl Exceptions - Centraliza todas as exceções do Axolotl.
"""

from .invalidkeyexception import InvalidKeyException
from .invalidkeyidexception import InvalidKeyIdException
from .invalidmessageexception import InvalidMessageException
from .invalidversionexception import InvalidVersionException
from .duplicatemessagexception import DuplicateMessageException
from .legacymessageexception import LegacyMessageException
from .nosessionexception import NoSessionException
from .statekeyexchangeexception import StaleKeyExchangeException
from .untrustedidentityexception import UntrustedIdentityException

__all__ = [
    "InvalidKeyException",
    "InvalidKeyIdException",
    "InvalidMessageException",
    "InvalidVersionException",
    "DuplicateMessageException",
    "LegacyMessageException",
    "NoSessionException",
    "StaleKeyExchangeException",
    "UntrustedIdentityException",
]

