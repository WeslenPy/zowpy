"""
Message Builder - Constrói nodes de mensagem para envio.

Cria mensagens de texto, mídia, etc. com criptografia E2E.
"""

import time
import uuid
from typing import Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.encryption.sender import EncryptionSender


class MessageBuilder:
    """
    Constrói nodes de mensagem para envio.
    
    Fluxo completo:
    1. Cria payload protobuf (Message.conversation, etc.)
    2. Serializa protobuf → bytes
    3. Criptografa bytes usando EncryptionSender
    4. Cria node com <enc> e <proto>
    5. Retorna node pronto para envio
    """
    
    def __init__(self, encryption_sender: EncryptionSender):
        """
        Inicializa builder.
        
        Args:
            encryption_sender: Sender para criptografar mensagens
        """
        self._encryption = encryption_sender
    
    async def build_text_message(
        self,
        to: str,
        text: str,
        message_id: Optional[str] = None,
        from_jid: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói mensagem de texto.
        
        Args:
            to: JID do destinatário
            text: Texto da mensagem
            message_id: ID da mensagem (gerado se None)
            from_jid: JID do remetente (opcional)
        
        Returns:
            ProtocolNode: Node de mensagem pronto para envio
        """
        logger.debug(f"Construindo mensagem de texto: to={to}, text_len={len(text)}")
        
        # 1. Gera ID se não fornecido
        if not message_id:
            message_id = self._generate_message_id()
        
        # 2. Cria protobuf Message
        from ...proto.e2e_pb2 import Message
        message = Message()
        message.conversation = text
        
        # 3. Serializa protobuf
        proto_bytes = message.SerializeToString()
        logger.debug(f"Protobuf serializado: {len(proto_bytes)} bytes")
        
        # 4. Identifica se é grupo
        is_group = self._is_group_jid(to)
        
        # 5. Criptografa
        enc_node = await self._encryption.encrypt_message(
            plaintext=proto_bytes,
            to_jid=to,
            is_group=is_group,
            media_type=None  # Texto não tem media_type
        )
        
        # 6. Cria node <proto> com dados originais
        proto_node = ProtocolNode(
            tag="proto",
            attributes={},
            data=proto_bytes
        )
        
        # 7. Cria node de mensagem completo
        message_node = ProtocolNode(
            tag="message",
            attributes={
                "to": to,
                "type": "text",
                "id": message_id,
                "t": str(int(time.time()))
            },
            children=[enc_node, proto_node]
        )
        
        if from_jid:
            message_node.attributes["from"] = from_jid
        
        logger.debug(f"Mensagem construída: id={message_id}, to={to}")
        return message_node
    
    async def build_media_message(
        self,
        to: str,
        media_type: str,
        media_data: bytes,
        caption: Optional[str] = None,
        message_id: Optional[str] = None,
        from_jid: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói mensagem de mídia.
        
        Args:
            to: JID do destinatário
            media_type: Tipo de mídia (image, audio, video, document)
            media_data: Dados da mídia (protobuf serializado)
            caption: Legenda (opcional)
            message_id: ID da mensagem (gerado se None)
            from_jid: JID do remetente (opcional)
        
        Returns:
            ProtocolNode: Node de mensagem pronto para envio
        """
        logger.debug(f"Construindo mensagem de mídia: to={to}, type={media_type}")
        
        # 1. Gera ID se não fornecido
        if not message_id:
            message_id = self._generate_message_id()
        
        # 2. Identifica se é grupo
        is_group = self._is_group_jid(to)
        
        # 3. Criptografa (media_data já é protobuf serializado)
        enc_node = await self._encryption.encrypt_message(
            plaintext=media_data,
            to_jid=to,
            is_group=is_group,
            media_type=media_type
        )
        
        # 4. Cria node <proto>
        proto_node = ProtocolNode(
            tag="proto",
            attributes={
                "mediatype": media_type
            },
            data=media_data
        )
        
        # 5. Cria node de mensagem
        message_node = ProtocolNode(
            tag="message",
            attributes={
                "to": to,
                "type": media_type,
                "id": message_id,
                "t": str(int(time.time()))
            },
            children=[enc_node, proto_node]
        )
        
        if from_jid:
            message_node.attributes["from"] = from_jid
        
        logger.debug(f"Mensagem de mídia construída: id={message_id}, type={media_type}")
        return message_node
    
    def _generate_message_id(self) -> str:
        """
        Gera ID único para mensagem.
        
        Returns:
            String com ID único
        """
        # Formato: timestamp-uuid
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4()).replace("-", "")[:8]
        return f"{timestamp}-{unique_id}"
    
    def _is_group_jid(self, jid: str) -> bool:
        """
        Verifica se JID é de grupo.
        
        Args:
            jid: JID a verificar
        
        Returns:
            True se é grupo, False caso contrário
        """
        return "-" in jid.split("@")[0] or "@g.us" in jid or "broadcast" in jid

