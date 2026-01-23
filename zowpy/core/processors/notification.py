"""
Notification Processor - Processa notifications recebidos.

Fluxo alinhado ao zowsuplib NOTIFICATION.md e protocol_notifications layer:
- Tipos pass (contacts, subject, w:gp2, devices): can_handle False → delegados a outros processors.
- psa: log e ignora, sem ACK.
- Demais tipos processados: classificar, emitir evento, sempre enviar ACK (id, class=notification, type, to=from, participant).
"""

from typing import Optional, Dict, Any, Callable, List
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter


PASS_TYPES: List[str] = ["contacts", "subject", "w:gp2", "devices"]


class NotificationProcessor(BaseProcessor):
    """Processa notifications recebidos (fluxo zowsuplib)."""

    def __init__(
        self,
        events: AsyncEventEmitter,
        flush_prekeys_fn: Optional[Callable] = None,
        get_keys_fn: Optional[Callable] = None,
        send_ack_fn: Optional[Callable] = None
    ):
        self._events = events
        self._flush_prekeys = flush_prekeys_fn
        self._get_keys = get_keys_fn
        self._send_ack = send_ack_fn

    def get_priority(self) -> int:
        return 5

    async def can_handle(self, node: ProtocolNode) -> bool:
        """False para tipos pass (contacts, subject, w:gp2, devices)."""
        if node.tag != "notification":
            return False
        ntype = node.get_attribute("type")
        if ntype in PASS_TYPES:
            return False
        return True

    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        notification_id = node.get_attribute("id")
        notification_type = node.get_attribute("type")
        from_jid = node.get_attribute("from")
        participant = node.get_attribute("participant")


        await self._send_ack_for_notification(
            notification_id, notification_type or "", from_jid, participant
        )

        logger.debug(
            "Processando notification: id=%s, type=%s, from=%s",
            notification_id, notification_type, from_jid
        )

        if notification_type == "psa":
            logger.info("Notification psa recebida, ignorando (zowsuplib)")
            return None

        if notification_type == "encrypt":
            await self._process_encrypt_notification(node)
            return None

        if notification_type == "privacy_token":
            logger.info(
                "Notification privacy_token de %s",
                from_jid.split("@")[0] if from_jid else ""
            )
            token_data: Optional[Dict[str, Any]] = None
            tokens = node.get_child("tokens")
            if tokens:
                items = []
                for child in (tokens.get_all_children() or []):
                    typ = child.get_attribute("type") if hasattr(child, "get_attribute") else None
                    data = getattr(child, "data", None)
                    items.append({"type": typ, "data": data})
                if items:
                    token_data = {"tokens": items}
            notification_data = {
                "id": notification_id,
                "type": notification_type,
                "from": from_jid,
                "participant": participant,
                "timestamp": node.get_attribute("t"),
            }
            if token_data:
                notification_data["token_data"] = token_data
            await self._events.emit("notification", notification_data)
            await self._send_ack_for_notification(
                notification_id, notification_type or "privacy_token", from_jid, participant
            )
            return notification_data

        # Demais tipos: mex, account_sync, link_code_companion_reg, registration,
        # business, disappearing_mode, picture, status, etc.
        notification_data = {
            "id": notification_id,
            "type": notification_type,
            "from": from_jid,
            "participant": participant,
            "timestamp": node.get_attribute("t"),
        }
        await self._events.emit("notification", notification_data)
    
        return notification_data

    async def _send_ack_for_notification(
        self,
        notification_id: str,
        notification_type: str,
        from_jid: str,
        participant: Optional[str] = None
    ) -> None:
        """Envia ACK para notification processada (id, notification, type, to, participant)."""
        if not self._send_ack or not from_jid or not notification_id:
            return
        ntype = notification_type or ""
        try:
            await self._send_ack(
                notification_id,
                "notification",
                ntype,
                from_jid,
                participant=participant
            )
        except Exception as e:
            logger.error("Erro ao enviar ACK de notification: %s", e)

    async def _process_encrypt_notification(self, node: ProtocolNode) -> None:
        """
        Processa notificação encrypt: ACK (com participant) + flush_prekeys ou get_keys.
        """
        notification_id = node.get_attribute("id")
        from_jid = node.get_attribute("from")
        participant = node.get_attribute("participant")

        await self._send_ack_for_notification(
            notification_id or "", "encrypt", from_jid or "", participant
        )

        count_node = node.get_child("count")
        identity_node = node.get_child("identity")

        if count_node:
            logger.info("Recebida RequestKeysEncryptNotification, enviando prekeys...")
            if self._flush_prekeys:
                try:
                    await self._flush_prekeys()
                except Exception as e:
                    logger.error("Erro ao processar RequestKeysEncryptNotification: %s", e)
            else:
                logger.warning(
                    "RequestKeysEncryptNotification recebida, mas flush_prekeys_fn não configurada"
                )
        elif identity_node:
            logger.info(
                "Recebida IdentityChangeEncryptNotification de %s, obtendo chaves...",
                from_jid
            )
            if self._get_keys:
                try:
                    success_jids, error_jids = await self._get_keys(from_jid)
                    if error_jids:
                        logger.warning(
                            "Erros ao obter chaves após mudança de identidade: %s",
                            error_jids
                        )
                    else:
                        logger.info("Chaves obtidas com sucesso para %s", from_jid)
                except Exception as e:
                    logger.error(
                        "Erro ao processar IdentityChangeEncryptNotification: %s", e
                    )
            else:
                logger.warning(
                    "IdentityChangeEncryptNotification recebida, mas get_keys_fn não configurada"
                )
        else:
            logger.debug("Notification encrypt sem <count> ou <identity>, ignorando")

