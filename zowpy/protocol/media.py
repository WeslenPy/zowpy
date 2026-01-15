"""
Async Media Handler - Handler de mídia totalmente assíncrono.

Refatora YowMediaProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncMediaHandler:
    """
    Handler de mídia totalmente assíncrono.
    Processa mensagens de mídia (imagem, áudio, vídeo, documento, etc.).
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_message(self, node: ProtocolNode) -> None:
        """
        Processa mensagem de mídia de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        message_type = node.get_attribute("type")

        if message_type == "medianotify":
            # Envia ACK
            await self._send_media_ack(node)
            return

        if message_type == "media":
            media_node = node.get_child("proto")
            if media_node is None:
                return

            media_type = media_node.get_attribute("mediatype")
            await self._handle_media_by_type(node, media_type)

    async def handle_iq(self, node: ProtocolNode) -> None:
        """
        Processa IQ relacionado a mídia (media conn) de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        # Processa resultado de media connection
        await self.events.emit("media:iq_result", {"node": node})

    async def send_media_connection_request(self) -> None:
        """Envia requisição para obter conexão de mídia."""
        await self.events.emit("media:request_connection", {})

    async def _handle_media_by_type(
        self, node: ProtocolNode, media_type: str
    ) -> None:
        """
        Processa mídia por tipo.

        :param node: Nó do protocolo
        :param media_type: Tipo de mídia
        """
        try:
            if media_type == "image":
                await self._handle_image(node)
            elif media_type == "sticker":
                await self._handle_sticker(node)
            elif media_type in ("audio", "ptt"):
                await self._handle_audio(node)
            elif media_type in ("video", "gif"):
                await self._handle_video(node)
            elif media_type == "location":
                await self._handle_location(node)
            elif media_type == "vcard":
                await self._handle_contact(node)
            elif media_type == "document":
                await self._handle_document(node)
            elif media_type == "url":
                await self._handle_extended_text(node)
            elif media_type == "buttons_response":
                await self._handle_buttons_response(node)
            elif media_type == "list_response":
                await self._handle_list_response(node)
            elif media_type == "product":
                await self._handle_product(node)
            elif media_type in ("1p_sticker", "avatar_sticker"):
                await self._handle_sticker(node)
            else:
                logger.warning(
                    f"Unsupported mediatype: {media_type}, will send receipts"
                )
                await self._send_media_ack(node)
        except Exception as e:
            logger.error(f"Error handling media type {media_type}: {e}")
            await self._send_media_ack(node)

    async def _handle_image(self, node: ProtocolNode) -> None:
        """Processa imagem."""
        await self.events.emit("media:image", {"node": node})

    async def _handle_sticker(self, node: ProtocolNode) -> None:
        """Processa sticker."""
        await self.events.emit("media:sticker", {"node": node})

    async def _handle_audio(self, node: ProtocolNode) -> None:
        """Processa áudio."""
        await self.events.emit("media:audio", {"node": node})

    async def _handle_video(self, node: ProtocolNode) -> None:
        """Processa vídeo."""
        await self.events.emit("media:video", {"node": node})

    async def _handle_location(self, node: ProtocolNode) -> None:
        """Processa localização."""
        await self.events.emit("media:location", {"node": node})

    async def _handle_contact(self, node: ProtocolNode) -> None:
        """Processa contato (vcard)."""
        await self.events.emit("media:contact", {"node": node})

    async def _handle_document(self, node: ProtocolNode) -> None:
        """Processa documento."""
        await self.events.emit("media:document", {"node": node})

    async def _handle_extended_text(self, node: ProtocolNode) -> None:
        """Processa texto estendido (URL)."""
        await self.events.emit("media:extended_text", {"node": node})

    async def _handle_buttons_response(
        self, node: ProtocolNode
    ) -> None:
        """Processa resposta de botões."""
        await self.events.emit("media:buttons_response", {"node": node})

    async def _handle_list_response(self, node: ProtocolNode) -> None:
        """Processa resposta de lista."""
        await self.events.emit("media:list_response", {"node": node})

    async def _handle_product(self, node: ProtocolNode) -> None:
        """Processa produto."""
        await self.events.emit("media:product", {"node": node})

    async def _send_media_ack(self, node: ProtocolNode) -> None:
        """Envia ACK de mídia."""
        await self.events.emit("media:ack", {"node": node})

