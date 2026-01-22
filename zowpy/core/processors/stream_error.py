"""
StreamError Processor - Processa stream:error recebidos.

Valida code/type/conflict antes de desconectar (só 503 → disconnect).
Alinhado ao zowsuplib onStreamError.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from .base import BaseProcessor
from ...core.events import AsyncEventEmitter

# Tipos de erro conhecidos (stream_error entity)
TYPE_CONFLICT = "conflict"
TYPE_ACK = "ack"
TYPE_XML_NOT_WELL_FORMED = "xml-not-well-formed"
TYPE_BAD_MAC = "bad-mac"
ERROR_TYPES = (TYPE_CONFLICT, TYPE_ACK, TYPE_XML_NOT_WELL_FORMED, TYPE_BAD_MAC)


class StreamErrorProcessor(BaseProcessor):
    """Processa stream:error. Emite 'stream:error'; o client valida e desconecta só se code=503."""

    def __init__(self, events: AsyncEventEmitter):
        self._events = events

    def get_priority(self) -> int:
        return 20

    async def can_handle(self, node: ProtocolNode) -> bool:
        return node.tag == "stream:error"

    def _error_data_from_children(self, node: ProtocolNode) -> Dict[str, Any]:
        """Monta dict tag -> data dos filhos (getErrorData)."""
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

    def _error_type_from_children(self, node: ProtocolNode) -> Optional[str]:
        """Primeiro filho cuja tag está em ERROR_TYPES (getErrorType)."""
        children = getattr(node, "children", []) or []
        for c in children:
            tag = getattr(c, "tag", None)
            if tag and tag in ERROR_TYPES:
                return tag
        return None

    def _is_conflict(self, node: ProtocolNode, error_type: Optional[str], attrs: dict) -> bool:
        """Confere se é conflict (sessão substituída)."""
        if error_type == TYPE_CONFLICT:
            return True
        reason = attrs.get("reason") or attrs.get("type")
        if reason in ("conflict", "replaced"):
            return True
        child_conflict = node.get_child("conflict") if hasattr(node, "get_child") else None
        if child_conflict is not None:
            return True
        return False

    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None,
    ) -> Optional[Dict[str, Any]]:
        attrs = getattr(node, "attributes", {}) or {}
        code = node.get_attribute("code") if hasattr(node, "get_attribute") else attrs.get("code")
        type_attr = node.get_attribute("type") if hasattr(node, "get_attribute") else attrs.get("type")
        reason = node.get_attribute("reason") if hasattr(node, "get_attribute") else attrs.get("reason")

        error_data = self._error_data_from_children(node)
        error_type = self._error_type_from_children(node) or type_attr
        is_conflict = self._is_conflict(node, error_type, attrs)

        logger.info(
            f"Stream error recebido: code={code}, type={error_type}, reason={reason}, is_conflict={is_conflict}",
        )
        logger.debug(f"Stream error node attributes={attrs}, error_data={error_data}")

        payload: Dict[str, Any] = {
            "node": node,
            "code": code,
            "type": error_type,
            "reason": reason,
            "error_data": error_data,
            "is_conflict": is_conflict,
        }
        await self._events.emit("stream:error", payload)
        return payload
