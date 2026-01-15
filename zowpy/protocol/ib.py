"""
Async IB Handler - Handler de IB (Identity/Backup) totalmente assíncrono.

Refatora YowIbProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncIBHandler:
    """
    Handler de IB totalmente assíncrono.
    Processa operações de identidade e backup.
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_iq(self, node: ProtocolNode) -> None:
        """
        Processa IQ relacionado a IB de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        await self.events.emit("ib:iq", {"node": node})

