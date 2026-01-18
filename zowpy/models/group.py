"""
Group Model - Modelo de grupo.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Group:
    """Modelo de grupo"""
    jid: str
    subject: Optional[str] = None
    participants: List[str] = None
    admins: List[str] = None
    creation_time: Optional[int] = None
    
    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.admins is None:
            self.admins = []








