"""
Message Model - Modelo de mensagem.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Message:
    """Modelo de mensagem"""
    id: str
    from_jid: str
    to_jid: str
    text: Optional[str] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_group: bool = False
    participant: Optional[str] = None









