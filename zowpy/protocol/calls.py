"""
Async Calls Handler - Handler de chamadas totalmente assíncrono.

Refatora YowCallsProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncCallsHandler:
    """
    Handler de chamadas totalmente assíncrono.
    Processa chamadas de voz/vídeo.
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_call(self, node: ProtocolNode) -> None:
        """
        Processa chamada de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        await self.events.emit("call", {"node": node})

