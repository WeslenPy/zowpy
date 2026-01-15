"""
Async Contacts Handler - Handler de contatos totalmente assíncrono.

Refatora YowContactsIqProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncContactsHandler:
    """
    Handler de contatos totalmente assíncrono.
    Processa operações de contatos (buscar, sincronizar, etc.).
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_iq(self, node: ProtocolNode) -> None:
        """
        Processa IQ relacionado a contatos de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        if node.get_attribute("type") == "result":
            await self._handle_contacts_result(node)
        elif node.get_attribute("type") == "error":
            await self._handle_contacts_error(node)

    async def send_sync_contacts(self, contacts: list[str]) -> None:
        """
        Envia requisição para sincronizar contatos.

        :param contacts: Lista de números de telefone
        """
        await self.events.emit("contacts:sync", {"contacts": contacts})

    async def send_get_contacts(self, contacts: list[str]) -> None:
        """
        Envia requisição para obter informações de contatos.

        :param contacts: Lista de números de telefone
        """
        await self.events.emit("contacts:get", {"contacts": contacts})

    async def _handle_contacts_result(self, node: ProtocolNode) -> None:
        """Processa resultado de operação de contatos."""
        await self.events.emit("contacts:result", {"node": node})

    async def _handle_contacts_error(self, node: ProtocolNode) -> None:
        """Processa erro de operação de contatos."""
        await self.events.emit("contacts:error", {"node": node})

