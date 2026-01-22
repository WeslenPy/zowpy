"""
IQ Processor - Processa IQs recebidos.

Fluxo alinhado ao IQ_FLOW.md e zowsuplib YowIqProtocolLayer / processIqRegistry:
1. Registry first: se ID no registry → process_iq_response, callback, return.
2. Se não no registry: recvIq-style (urn:xmpp:ping → pong; md; error; result por filhos).
"""

import asyncio
from typing import Optional, Dict, Any, Callable, List
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter
from ...core.processors.iq_response import IQResponseProcessor


def _result_type_from_children(node: ProtocolNode) -> Optional[str]:
    """
    Identifica tipo de IQ result pelos filhos (paridade zowsuplib recvIq).
    Retorna tag do primeiro filho relevante ou None.
    """
    if not node.has_children():
        return None
    # Ordem de verificação conforme layer.py
    for tag in (
        "verified_name", "media_conn", "cat", "list", "usync", "companion-props",
        "groups", "group", "account", "email", "verify_email", "device_logout",
        "count", "picture", "result", "sync"
    ):
        if node.get_child(tag) is not None:
            return tag
    return None


class IQProcessor(BaseProcessor):
    """Processa IQs recebidos (fluxo IQ_FLOW / zowsuplib)."""

    def __init__(
        self,
        events: AsyncEventEmitter,
        iq_response_processor: Optional[IQResponseProcessor] = None,
        send_node_fn: Optional[Callable] = None,
        got_pong_fn: Optional[Callable[[str], Any]] = None,
    ):
        self._events = events
        self._iq_response_processor = iq_response_processor
        self._send_node_fn = send_node_fn
        self._got_pong_fn = got_pong_fn
        self._iq_handlers: Dict[str, Callable] = {}

    def get_priority(self) -> int:
        return 8

    async def can_handle(self, node: ProtocolNode) -> bool:
        return node.tag == "iq"

    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        iq_id = node.get_attribute("id")
        iq_type = node.get_attribute("type")
        iq_xmlns = node.get_attribute("xmlns")
        from_jid = node.get_attribute("from")
        to_jid = node.get_attribute("to")

        logger.debug(
            "Processando IQ: id=%s, type=%s, xmlns=%s, from=%s",
            iq_id, iq_type, iq_xmlns, from_jid
        )

        # 1. Registry first (IQ_FLOW: processIqRegistry antes de recvIq)
        if self._iq_response_processor and iq_id and iq_type in ("result", "error"):
            processed = False
            try:
                processed = await self._iq_response_processor.process_iq_response(node)
            except Exception as e:
                logger.error("Erro ao processar IQ response para %s: %s", iq_id, e, exc_info=True)
            if processed:
                logger.debug("IQ %s processado por registry (callback), retornando", iq_id)
                return {"id": iq_id, "type": iq_type, "xmlns": iq_xmlns, "from": from_jid, "to": to_jid, "handled_by_registry": True}

        # 2. Não no registry → recvIq-style

        # 2a. urn:xmpp:ping → responde Pong automaticamente
        if iq_xmlns == "urn:xmpp:ping" and self._send_node_fn:
            from ...utils.constants import YowConstants
            pong_node = ProtocolNode(
                tag="iq",
                attributes={"id": ProtocolNode._generateId(), "type": "result", "to": YowConstants.DOMAIN,},
                children=[]
            )
            try:
                await self._send_node_fn(pong_node)
                logger.debug("Pong enviado em resposta ao ping %s", iq_id)
            except Exception as e:
                logger.error("Erro ao enviar pong para ping %s: %s", iq_id, e, exc_info=True)
            return {
                "id": iq_id, "type": iq_type, "xmlns": iq_xmlns,
                "from": from_jid, "to": to_jid, "pong_sent": True,
            }

        # 2b. xmlns md (MultiDevice)
        if iq_xmlns == "md":
            pair_device = node.get_child("pair-device")
            pair_success = node.get_child("pair-success")
            md_kind = "pair-device" if pair_device else ("pair-success" if pair_success else "md")
            iq_data = {
                "id": iq_id, "type": iq_type, "xmlns": iq_xmlns,
                "from": from_jid, "to": to_jid, "md_kind": md_kind,
            }
            await self._events.emit("iq", iq_data)
            await self._run_xmlns_handler(node, iq_data)
            return iq_data

        # 2c. type error
        if iq_type == "error":
            iq_data = {
                "id": iq_id, "type": iq_type, "xmlns": iq_xmlns,
                "from": from_jid, "to": to_jid, "result_type": "error",
            }
            await self._events.emit("iq", iq_data)
            await self._events.emit("iq:error", iq_data)
            await self._run_xmlns_handler(node, iq_data)
            return iq_data

        # 2d. type result
        if iq_type == "result":
            # w:p sem filhos = pong de ping (IQ_FLOW); gotPong se disponível (pongs não registrados)
            if iq_xmlns == "w:p" and not node.has_children():
                if iq_id and self._got_pong_fn and callable(self._got_pong_fn):
                    try:
                        res = self._got_pong_fn(iq_id)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as e:
                        logger.warning("got_pong_fn para %s: %s", iq_id, e)
                return {
                    "id": iq_id, "type": iq_type, "xmlns": iq_xmlns,
                    "from": from_jid, "to": to_jid, "result_type": "pong",
                }

            result_type = _result_type_from_children(node)
            iq_data = {
                "id": iq_id, "type": iq_type, "xmlns": iq_xmlns,
                "from": from_jid, "to": to_jid, "result_type": result_type or "generic",
            }
            await self._events.emit("iq", iq_data)
            await self._run_xmlns_handler(node, iq_data)
            return iq_data

        # 2e. Outros (get/set etc.)
        iq_data = {
            "id": iq_id, "type": iq_type, "xmlns": iq_xmlns,
            "from": from_jid, "to": to_jid,
        }
        await self._events.emit("iq", iq_data)
        await self._run_xmlns_handler(node, iq_data)
        return iq_data

    async def _run_xmlns_handler(self, node: ProtocolNode, iq_data: Dict[str, Any]) -> None:
        xmlns = iq_data.get("xmlns")
        if not xmlns or xmlns not in self._iq_handlers:
            return
        try:
            fn = self._iq_handlers[xmlns]
            res = fn(node, iq_data)
            if asyncio.iscoroutine(res):
                await res
        except Exception as e:
            logger.error("Erro em IQ handler xmlns=%s: %s", xmlns, e, exc_info=True)

    def register_handler(self, xmlns: str, handler: Callable) -> None:
        self._iq_handlers[xmlns] = handler
        logger.debug("Handler registrado para IQ xmlns: %s", xmlns)
