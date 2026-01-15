"""
Async Groups Handler - Handler de grupos totalmente assíncrono.

Refatora YowGroupsProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncGroupsHandler:
    """
    Handler de grupos totalmente assíncrono.
    Processa operações de grupos (criar, listar, adicionar membros, etc.).
    """

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_iq(self, node: ProtocolNode) -> None:
        """
        Processa IQ relacionado a grupos de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        if node.get_attribute("type") == "result":
            r_node = node.get_child(0)
            if r_node is None:
                # Processa em protocol_iq
                pass
            elif r_node.tag == "groups":
                # Lista de grupos
                await self._handle_list_groups_result(node)
            elif r_node.tag == "group":
                # Info de grupo, criar grupo ou join
                await self._handle_group_result(node)
            elif r_node.tag == "add":
                await self._handle_add_participants_result(node)
            elif r_node.tag == "remove":
                await self._handle_remove_participants_result(node)
            elif r_node.tag == "promote":
                await self._handle_promote_result(node)
            elif r_node.tag == "demote":
                await self._handle_demote_result(node)
            elif r_node.tag == "leave":
                await self._handle_leave_result(node)
            elif r_node.tag == "invite":
                await self._handle_invite_code_result(node)
            elif r_node.tag in [
                "locked",
                "unlocked",
                "announcement",
                "not_announcement",
                "membership_approval_mode",
                "membership_requests_action",
            ]:
                await self._handle_setting_result(node)

    async def handle_notification(self, node: ProtocolNode) -> None:
        """
        Processa notificações de grupos de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        if node.get_attribute("type") == "w:gp2":
            r_node = node.get_child(0)
            if r_node.tag == "subject":
                await self._handle_subject_notification(node)
            elif r_node.tag == "create":
                if r_node.get_attribute("reason") is not None:
                    await self._handle_invite_notification(node)
                else:
                    await self._handle_create_notification(node)
            elif r_node.tag == "remove":
                await self._handle_remove_notification(node)
            elif r_node.tag == "add":
                await self._handle_add_notification(node)

    async def send_create_group(
        self, participants: list[str], subject: str
    ) -> None:
        """
        Envia requisição para criar grupo.

        :param participants: Lista de participantes (JIDs)
        :param subject: Assunto do grupo
        """
        # Cria nó do protocolo e emite evento para envio
        await self.events.emit("groups:create", {
            "participants": participants,
            "subject": subject,
        })

    async def send_list_groups(self) -> None:
        """Envia requisição para listar grupos."""
        await self.events.emit("groups:list", {})

    async def send_group_info(self, group_jid: str) -> None:
        """
        Envia requisição para obter info do grupo.

        :param group_jid: JID do grupo
        """
        await self.events.emit("groups:info", {"group_jid": group_jid})

    async def send_add_participants(
        self, group_jid: str, participants: list[str]
    ) -> None:
        """
        Envia requisição para adicionar participantes.

        :param group_jid: JID do grupo
        :param participants: Lista de participantes
        """
        await self.events.emit("groups:add", {
            "group_jid": group_jid,
            "participants": participants,
        })

    async def send_remove_participants(
        self, group_jid: str, participants: list[str]
    ) -> None:
        """
        Envia requisição para remover participantes.

        :param group_jid: JID do grupo
        :param participants: Lista de participantes
        """
        await self.events.emit("groups:remove", {
            "group_jid": group_jid,
            "participants": participants,
        })

    async def _handle_list_groups_result(self, node: ProtocolNode) -> None:
        """Processa resultado de listagem de grupos."""
        await self.events.emit("groups:list_result", {"node": node})

    async def _handle_group_result(self, node: ProtocolNode) -> None:
        """Processa resultado de operação de grupo."""
        await self.events.emit("groups:result", {"node": node})

    async def _handle_add_participants_result(
        self, node: ProtocolNode
    ) -> None:
        """Processa resultado de adição de participantes."""
        await self.events.emit("groups:add_result", {"node": node})

    async def _handle_remove_participants_result(
        self, node: ProtocolNode
    ) -> None:
        """Processa resultado de remoção de participantes."""
        await self.events.emit("groups:remove_result", {"node": node})

    async def _handle_promote_result(self, node: ProtocolNode) -> None:
        """Processa resultado de promoção."""
        await self.events.emit("groups:promote_result", {"node": node})

    async def _handle_demote_result(self, node: ProtocolNode) -> None:
        """Processa resultado de rebaixamento."""
        await self.events.emit("groups:demote_result", {"node": node})

    async def _handle_leave_result(self, node: ProtocolNode) -> None:
        """Processa resultado de saída do grupo."""
        await self.events.emit("groups:leave_result", {"node": node})

    async def _handle_invite_code_result(
        self, node: ProtocolNode
    ) -> None:
        """Processa resultado de código de convite."""
        await self.events.emit("groups:invite_code_result", {"node": node})

    async def _handle_setting_result(self, node: ProtocolNode) -> None:
        """Processa resultado de configuração."""
        await self.events.emit("groups:setting_result", {"node": node})

    async def _handle_subject_notification(
        self, node: ProtocolNode
    ) -> None:
        """Processa notificação de mudança de assunto."""
        await self.events.emit("groups:subject_notification", {"node": node})

    async def _handle_create_notification(
        self, node: ProtocolNode
    ) -> None:
        """Processa notificação de criação de grupo."""
        await self.events.emit("groups:create_notification", {"node": node})

    async def _handle_invite_notification(
        self, node: ProtocolNode
    ) -> None:
        """Processa notificação de convite."""
        await self.events.emit("groups:invite_notification", {"node": node})

    async def _handle_remove_notification(
        self, node: ProtocolNode
    ) -> None:
        """Processa notificação de remoção."""
        await self.events.emit("groups:remove_notification", {"node": node})

    async def _handle_add_notification(self, node: ProtocolNode) -> None:
        """Processa notificação de adição."""
        await self.events.emit("groups:add_notification", {"node": node})

