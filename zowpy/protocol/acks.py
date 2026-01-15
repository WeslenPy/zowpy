"""
Async Acks Handler - Handler de ACKs totalmente assíncrono.

Refatora YowAckProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncAcksHandler:
    """
    Handler de ACKs totalmente assíncrono.
    Processa confirmações de mensagens.
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_ack(self, node: ProtocolNode) -> None:
        """
        Processa ACK de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        await self.events.emit("ack", {"node": node})

    async def send_ack(self, message_id: str, jid: str) -> None:
        """
        Envia ACK de mensagem.

        :param message_id: ID da mensagem
        :param jid: JID do remetente
        """
        await self.events.emit("ack:send", {
            "message_id": message_id,
            "jid": jid,
        })

