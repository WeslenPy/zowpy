"""
Async Chatstate Handler - Handler de estado de chat totalmente assíncrono.

Refatora YowChatstateProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncChatstateHandler:
    """
    Handler de estado de chat totalmente assíncrono.
    Processa estados de chat (digitando, gravando, etc.).
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_message(self, node: ProtocolNode) -> None:
        """
        Processa mensagem de estado de chat de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        chatstate = node.get_child("composing") or node.get_child("recording") or node.get_child("paused")
        if chatstate:
            state_type = chatstate.tag
            await self.events.emit("chatstate", {
                "type": state_type,
                "node": node,
            })

    async def send_composing(self, jid: str) -> None:
        """
        Envia estado "digitando".

        :param jid: JID do destinatário
        """
        await self.events.emit("chatstate:composing", {"jid": jid})

    async def send_paused(self, jid: str) -> None:
        """
        Envia estado "pausado".

        :param jid: JID do destinatário
        """
        await self.events.emit("chatstate:paused", {"jid": jid})

