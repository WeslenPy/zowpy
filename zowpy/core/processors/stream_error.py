"""
StreamError Processor - Processa stream:error recebidos.

Ao receber <stream:error code="503" /> (ou outro), emite evento e a conta
deve ser desconectada (handler no client).
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from .base import BaseProcessor
from ...core.events import AsyncEventEmitter


class StreamErrorProcessor(BaseProcessor):
    """Processa stream:error. Emite 'stream:error'; o client desconecta ao receber."""

    def __init__(self, events: AsyncEventEmitter):
        self._events = events

    def get_priority(self) -> int:
        """Alta prioridade para tratar stream:error antes de outros."""
        return 20

    async def can_handle(self, node: ProtocolNode) -> bool:
        return node.tag == "stream:error"

    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None,
    ) -> Optional[Dict[str, Any]]:
        code = node.get_attribute("code") if hasattr(node, "get_attribute") else None
        error_type = node.get_attribute("type") if hasattr(node, "get_attribute") else None
        logger.error(f"Stream error recebido (code={code}, type={error_type}); desconectando conta")
        attrs = getattr(node, "attributes", {})
        logger.debug(f"Stream error node: tag={node.tag}, attributes={attrs}")

        payload: Dict[str, Any] = {
            "node": node,
            "code": code,
            "type": error_type,
        }
        await self._events.emit("stream:error", payload)
        return payload
