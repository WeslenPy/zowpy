"""
Failure Processor - Processa nodes <failure> recebidos.

Usado quando o servidor envia <failure> no stream (ex.: após auth ou em erros de protocolo).
Alinhado ao zowsuplib FailureProtocolEntity e handleFailure no auth layer.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from .base import BaseProcessor
from ...core.events import AsyncEventEmitter


class FailureProcessor(BaseProcessor):
    """Processa nodes <failure>. Emite evento 'failure' com code, reason e payload."""

    def __init__(self, events: AsyncEventEmitter):
        self._events = events

    def get_priority(self) -> int:
        return 18

    async def can_handle(self, node: ProtocolNode) -> bool:
        return node.tag == "failure"

    def _children_data(self, node: ProtocolNode) -> Dict[str, Any]:
        """Extrai tag -> data dos filhos (para reason, conflict, etc.)."""
        data: Dict[str, Any] = {}
        children = getattr(node, "children", []) or []
        for c in children:
            if hasattr(c, "tag"):
                key = c.tag
                val = getattr(c, "data", None)
                if val is not None and isinstance(val, bytes):
                    try:
                        val = val.decode("utf-8", errors="replace")
                    except Exception:
                        pass
                data[key] = val
        return data

    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None,
    ) -> Optional[Dict[str, Any]]:
        attrs = getattr(node, "attributes", {}) or {}
        code = node.get_attribute("code") if hasattr(node, "get_attribute") else attrs.get("code")
        reason = node.get_attribute("reason") if hasattr(node, "get_attribute") else attrs.get("reason")
        children_data = self._children_data(node)

        logger.error(
            "Failure recebido: code=%s, reason=%s",
            code or "(vazio)",
            reason or "(vazio)",
        )
        logger.debug("Failure node attributes=%s, children_data=%s", attrs, children_data)

        payload: Dict[str, Any] = {
            "node": node,
            "code": code,
            "reason": reason,
            "attributes": dict(attrs),
            "children_data": children_data,
        }
        await self._events.emit("failure", payload)
        return payload
