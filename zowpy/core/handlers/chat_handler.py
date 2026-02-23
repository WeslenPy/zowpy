"""
Chat Handler - Gerencia configurações de chat (mensagens efêmeras, etc.).

Baseado em setDisappearing do yowbot_layer (zowsuplib).
"""

import time
from typing import Optional

from ...protocol.structs import ProtocolNode
from ...protocol.entities.message import ProtomessageProtocolEntity
from ...protocol.entities.attributes.attributes_message import MessageAttributes
from ...protocol.entities.attributes.attributes_message_key import MessageKeyAttributes
from ...protocol.entities.attributes.attributes_message_meta import MessageMetaAttributes
from ...protocol.entities.attributes.attributes_protocol import ProtocolAttributes
from ...protocol.entities.attributes.attributes_disappearing_mode import DisappearingModeAttributes
from ...utils.tools import WATools


class ChatHandler:
    """
    Handler para operações de chat (configurações de conversa).
    """

    def __init__(self, send_message_fn: callable):
        """
        Inicializa o handler.

        Args:
            send_message_fn: Função async que recebe um ProtocolNode e envia a mensagem
                             (ex.: client.process_plaintext_node_and_send).
        """
        self._send_message = send_message_fn

    async def set_disappearing(
        self,
        chat_jid: str,
        disappearing_days: Optional[int] = None,
    ) -> str:
        """
        Define mensagens efêmeras (desaparecidas) no chat.

        Equivalente a setDisappearing do yowbot_layer: envia protocol message
        TYPE_EPHEMERAL_SETTING com ephemeral_expiration e disappearing_mode.

        Args:
            chat_jid: JID do chat (contato ou grupo), ex.: 5511999999999 ou 5511999999999@g.us
            disappearing_days: Número de dias para as mensagens sumirem.
                              None ou 1 = 1 dia (86400 s); 2 = 2 dias; 0 = desliga (não suportado pelo servidor como 0, use 1 dia).

        Returns:
            ID da mensagem enviada.
        """
        if disappearing_days is None or disappearing_days == 1:
            disappearing_time = 86400  # 1 dia em segundos
        else:
            disappearing_time = int(disappearing_days) * 86400

        normalized_jid = WATools.normalizeJid(chat_jid).split(",")[0].strip()

        key_attr = MessageKeyAttributes(
            id=None,
            from_me=True,
            remote_jid=normalized_jid,
        )

        protocol_attr = ProtocolAttributes(
            key=key_attr,
            type=ProtocolAttributes.TYPE_EPHEMERAL_SETTING,
            ephemeral_expiration=disappearing_time,
            disappearing_mode=DisappearingModeAttributes(
                trigger=DisappearingModeAttributes.TRIGGER_CHAT_SETTING,
                initiatedByMe=True,
            ),
            timestamp_ms=int(time.time() * 1000),
        )

        message_id = ProtocolNode.generate_key()
        meta_attr = MessageMetaAttributes(
            id=message_id,
            recipient=normalized_jid,
            timestamp=int(time.time()),
        )

        message_attributes = MessageAttributes(protocol=protocol_attr)
        entity = ProtomessageProtocolEntity(
            message_attributes=message_attributes,
            message_meta_attributes=meta_attr,
        )

        node = entity.to_protocol_node()
        await self._send_message(node)
        return message_id


    async def set_disappearing_disabled(
        self,
        chat_jid: str,
    ) -> str:
        """
        Define mensagens efêmeras (desaparecidas) no chat.

        Equivalente a setDisappearing do yowbot_layer: envia protocol message
        TYPE_EPHEMERAL_SETTING com ephemeral_expiration e disappearing_mode.

        Args:
            chat_jid: JID do chat (contato ou grupo), ex.: 5511999999999 ou 5511999999999@g.us
            disappearing_days: Número de dias para as mensagens sumirem.
                              None ou 1 = 1 dia (86400 s); 2 = 2 dias; 0 = desliga (não suportado pelo servidor como 0, use 1 dia).

        Returns:
            ID da mensagem enviada.
        """

        normalized_jid = WATools.normalizeJid(chat_jid).split(",")[0].strip()

        key_attr = MessageKeyAttributes(
            id=None,
            from_me=True,
            remote_jid=normalized_jid,
        )

        protocol_attr = ProtocolAttributes(
            key=key_attr,
            type=ProtocolAttributes.TYPE_EPHEMERAL_SETTING,
            ephemeral_expiration=0,
            disappearing_mode=DisappearingModeAttributes(
                trigger=DisappearingModeAttributes.TRIGGER_UNKNOWN,
            ),
        )

        message_id = ProtocolNode.generate_key()
        meta_attr = MessageMetaAttributes(
            id=message_id,
            recipient=normalized_jid,
            timestamp=int(time.time()),
        )

        message_attributes = MessageAttributes(protocol=protocol_attr)
        entity = ProtomessageProtocolEntity(
            message_attributes=message_attributes,
            message_meta_attributes=meta_attr,
        )

        node = entity.to_protocol_node()
        await self._send_message(node)
        return message_id
