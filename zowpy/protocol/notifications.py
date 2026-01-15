"""
Async Notifications Handler - Handler de notificações totalmente assíncrono.

Refatora YowNotificationsProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncNotificationsHandler:
    """
    Handler de notificações totalmente assíncrono.
    Processa notificações do WhatsApp.
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_notification(self, node: ProtocolNode) -> None:
        """
        Processa notificação de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        notification_type = node.get_attribute("type")
        await self.events.emit("notification", {
            "type": notification_type,
            "node": node,
        })

