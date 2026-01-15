"""
Async Profiles Handler - Handler de perfis totalmente assíncrono.

Refatora YowProfilesProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncProfilesHandler:
    """
    Handler de perfis totalmente assíncrono.
    Processa operações de perfis (obter, atualizar, etc.).
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_iq(self, node: ProtocolNode) -> None:
        """
        Processa IQ relacionado a perfis de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        await self.events.emit("profiles:iq", {"node": node})

    async def send_get_profile(self, jid: str) -> None:
        """
        Envia requisição para obter perfil.

        :param jid: JID do usuário
        """
        await self.events.emit("profiles:get", {"jid": jid})

