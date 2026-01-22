"""
Receipt Processor - Processa receipts recebidos.

Fluxo alinhado ao zowsuplib RECEIPTS_FLOW:
- Retry: ACK imediato → busca mensagem na fila → reenvia se encontrada.
- Normal: MSG_LOG (READ/RECEIVED) → entity.ack() → envia ACK ao servidor.
"""

from typing import Optional, Dict, Any, Callable, List
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter


class ReceiptProcessor(BaseProcessor):
    """Processa receipts recebidos (fluxo zowsuplib)."""

    def __init__(
        self,
        events: AsyncEventEmitter,
        get_enqueued_message_fn: Optional[Callable] = None,
        resend_message_fn: Optional[Callable] = None,
    ):
        self._events = events
        self._get_enqueued_message = get_enqueued_message_fn
        self._resend_message = resend_message_fn

    def get_priority(self) -> int:
        return 5

    async def can_handle(self, node: ProtocolNode) -> bool:
        return node.tag == "receipt"

    def _parse_items(self, node: ProtocolNode) -> Optional[List[str]]:
        """Extrai lista de IDs de <list><item id="..."/> (múltiplas mensagens)."""
        list_node = node.get_child("list")
        if not list_node:
            return None
        items: List[str] = []
        for child in list_node.get_all_children("item"):
            sid = child.get_attribute("id") if hasattr(child, "get_attribute") else None
            if sid:
                items.append(sid)
        return items if items else None

    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None,
    ) -> Optional[Dict[str, Any]]:
        receipt_id = node.get_attribute("id")
        receipt_type = node.get_attribute("type")
        from_jid = node.get_attribute("from")
        participant = node.get_attribute("participant")
        offline = node.get_attribute("offline")
        timestamp = node.get_attribute("t")


        logger.debug(f"Recebido receipt: {node}")
        logger.debug(f"Processando receipt: id={receipt_id}, type={receipt_type}, from={from_jid}")

        if receipt_type == "retry":
            await self._process_retry_receipt(node)
            return None

        items = self._parse_items(node)
        status = "read" if receipt_type == "read" else "received"
        receipt_data: Dict[str, Any] = {
            "id": receipt_id,
            "type": receipt_type,
            "from": from_jid,
            "participant": participant,
            "timestamp": timestamp,
            "offline": offline,
            "items": items,
            "status": status,
        }

        await self._events.emit("receipt", receipt_data)
        await self._events.emit("msg_log", {"status": status, **receipt_data})
        

        if receipt_type is None:
            await self._send_ack_for_receipt(
                message_id=receipt_id,
                to=from_jid,
                receipt_type=None,
                participant=None,
            )


        return receipt_data

    async def _send_ack_for_receipt(
        self,
        message_id: str,
        to: str,
        receipt_type: Optional[str],
        participant: Optional[str],
    ) -> None:
        """Envia ACK do receipt (entity.ack() → OutgoingAckProtocolEntity)."""
        from ...core.builders.receipt_builder import ReceiptBuilder

        ack_node = ReceiptBuilder.build_ack(
            message_id=message_id,
            to=to,
            receipt_type=receipt_type or "",
            participant=participant,
            ack_class="receipt",
        )
        await self._events.emit("ack:send", {"node": ack_node})
        logger.debug(f"ACK de receipt enviado: id={message_id}, type={receipt_type or 'delivered'}, to={to}")
    
    async def _process_retry_receipt(self, node: ProtocolNode) -> None:
        """
        Processa receipt de retry (fluxo zowsuplib AxolotlSendLayer).

        1. Envia ACK imediato (retryReceiptEntity.ack()).
        2. Busca mensagem na sentQueue (getEnqueuedMessageNode).
        3. Se encontrada: getKeysFor → re-encripta e reenvia. Se não: ignora.
        """
        receipt_id = node.get_attribute("id")
        from_jid = node.get_attribute("from")
        participant = node.get_attribute("participant")
        receipt_type = node.get_attribute("type")

        logger.info(f"Recebido retry receipt: id={receipt_id}, from={from_jid}, participant={participant}")

        retry_node = node.get_child("retry")
        retry_count = 0
        retry_jid = None
        if retry_node:
            count_attr = retry_node.get_attribute("count")
            if count_attr:
                try:
                    retry_count = int(count_attr)
                except (ValueError, TypeError):
                    retry_count = 0
        jid_node = node.get_child("jid")
        if jid_node and getattr(jid_node, "data", None):
            d = jid_node.data
            retry_jid = d.decode() if isinstance(d, bytes) else str(d)
        else:
            retry_jid = participant or from_jid
        logger.debug(f"Retry info: count={retry_count}, jid={retry_jid}")

        try:
            from ...core.builders.receipt_builder import ReceiptBuilder

            ack_node = ReceiptBuilder.build_ack(
                message_id=receipt_id,
                to=from_jid,
                receipt_type=receipt_type or "retry",
                participant=participant,
                ack_class="receipt",
            )
            await self._events.emit("ack:send", {"node": ack_node})
            logger.info(f"ACK de retry enviado: id={receipt_id}, to={from_jid}")
        except Exception as e:
            logger.error(f"Erro ao enviar ACK do retry: {e}", exc_info=True)
            return

        if not self._get_enqueued_message:
            logger.warning("get_enqueued_message_fn não configurada, ignorando retry")
            return
        try:
            message_node = await self._get_enqueued_message(receipt_id, keep_enqueued=True)
            if message_node:
                logger.info(f"Mensagem encontrada para retry {receipt_id}, re-enviando...")
                if self._resend_message:
                    await self._resend_message(message_node, retry_jid, retry_count)
                else:
                    logger.warning("resend_message_fn não configurada")
            else:
                logger.debug(f"Mensagem não encontrada na fila para retry {receipt_id}, ignorando")
        except Exception as e:
            logger.error(f"Erro ao processar retry receipt: {e}", exc_info=True)

