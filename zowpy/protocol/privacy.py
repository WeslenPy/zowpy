"""
Async Privacy Handler - Handler de privacidade totalmente assíncrono.

Refatora YowPrivacyProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncPrivacyHandler:
    """
    Handler de privacidade totalmente assíncrono.
    Processa configurações de privacidade.
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_iq(self, node: ProtocolNode) -> None:
        """
        Processa IQ relacionado a privacidade de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        await self.events.emit("privacy:iq", {"node": node})

    async def send_set_privacy(self, settings: dict) -> None:
        """
        Envia requisição para definir configurações de privacidade.

        :param settings: Configurações de privacidade
        """
        await self.events.emit("privacy:set", {"settings": settings})

