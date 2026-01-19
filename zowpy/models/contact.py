"""
Contact Model - Modelo de contato.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Contact:
    """Modelo de contato"""
    jid: str
    name: Optional[str] = None
    push_name: Optional[str] = None
    is_business: bool = False
    is_verified: bool = False









