"""
Processors - Sistema moderno de processamento de protocol nodes.

Arquitetura baseada em processors ao invés de layers, mais limpa e fácil de manter.
"""

from .base import BaseProcessor
from .router import NodeRouter
from .registry import ProcessorRegistry

__all__ = [
    "BaseProcessor",
    "NodeRouter",
    "ProcessorRegistry",
]

