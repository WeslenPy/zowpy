"""
Encryption Sender - Criptografa mensagens para envio.

Baseado no zowsuplib AxolotlSendLayer, mas totalmente assíncrono e moderno.
"""

from typing import Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...db.manager import AxolotlManager
from ...axolotl import exceptions
from ...axolotl.protocol.whispermessage import WhisperMessage
from ...axolotl.protocol.prekeywhispermessage import PreKeyWhisperMessage
from ...utils.tools import WATools


class EncryptionSender:
    """
    Criptografa mensagens E2E para envio.
    
    Baseado no zowsuplib AxolotlSendLayer.processPlaintextNodeAndSend(), mas totalmente assíncrono.
    
    Suporta:
    - Mensagens individuais (MSG ou PKMSG)
    - Mensagens de grupo (SKMSG)
    """
    
    # Tipos de mensagem criptografada
    TYPE_SKMSG = "skmsg"
    TYPE_PKMSG = "pkmsg"
    TYPE_MSG = "msg"
    
    def __init__(self, manager: AxolotlManager):
        """
        Inicializa sender.
        
        Args:
            manager: AxolotlManager para criptografia
        """
        self._manager = manager
    
    async def encrypt_message(
        self,
        plaintext: bytes,
        to_jid: str,
        is_group: bool = False,
        media_type: Optional[str] = None
    ) -> ProtocolNode:
        """
        Criptografa mensagem E2E.
        
        Baseado em AxolotlSendLayer.sendToContact() e sendToGroup().
        
        Args:
            plaintext: Dados em plaintext (protobuf Message serializado)
            to_jid: JID do destinatário
            is_group: Se é mensagem de grupo
            media_type: Tipo de mídia (opcional)
        
        Returns:
            ProtocolNode: Node com <enc> contendo mensagem criptografada
        
        Raises:
            exceptions.NoSessionException: Se não há sessão (para grupos)
        """
        logger.debug(f"Criptografando mensagem: to={to_jid}, is_group={is_group}, plaintext_len={len(plaintext)}")
        
        if is_group:
            # Mensagem de grupo (SKMSG)
            return await self._encrypt_group_message(plaintext, to_jid, media_type)
        else:
            # Mensagem individual (MSG ou PKMSG)
            return await self._encrypt_contact_message(plaintext, to_jid, media_type)
    
    async def _encrypt_group_message(
        self,
        plaintext: bytes,
        group_jid: str,
        media_type: Optional[str] = None
    ) -> ProtocolNode:
        """
        Criptografa mensagem de grupo (SKMSG).
        
        Baseado em AxolotlSendLayer.sendToGroupWithSessions().
        """
        logger.debug(f"Criptografando mensagem de grupo: group={group_jid}")
        
        try:
            # Criptografa usando sender key do grupo
            ciphertext = await self._manager.group_encrypt(group_jid, plaintext)
            
            # Cria node <enc> com SKMSG
            enc_node = ProtocolNode(
                tag="enc",
                attributes={
                    "type": self.TYPE_SKMSG,
                    "v": "2"
                },
                data=ciphertext
            )
            
            if media_type:
                enc_node.attributes["mediatype"] = media_type
            
            logger.debug(f"Mensagem de grupo criptografada: {len(ciphertext)} bytes")
            return enc_node
        
        except exceptions.NoSessionException:
            # Sender key não existe, criar antes de criptografar
            logger.warning(f"Sender key não encontrado para grupo {group_jid}, criando...")
            await self._manager.group_create_skmsg(group_jid)
            # Tentar criptografar novamente
            ciphertext = await self._manager.group_encrypt(group_jid, plaintext)
            
            enc_node = ProtocolNode(
                tag="enc",
                attributes={
                    "type": self.TYPE_SKMSG,
                    "v": "2"
                },
                data=ciphertext
            )
            
            if media_type:
                enc_node.attributes["mediatype"] = media_type
            
            return enc_node
    
    async def _encrypt_contact_message(
        self,
        plaintext: bytes,
        to_jid: str,
        media_type: Optional[str] = None
    ) -> ProtocolNode:
        """
        Criptografa mensagem individual (MSG ou PKMSG).
        
        Baseado em AxolotlSendLayer.sendToPeerWithSessions().
        """
        logger.debug(f"Criptografando mensagem individual: to={to_jid}")
        
        # Extrai recipient ID do JID
        recipient_id = to_jid.split('@')[0]
        
        # Criptografa (retorna WhisperMessage ou PreKeyWhisperMessage)
        ciphertext = await self._manager.encrypt(recipient_id, plaintext)
        
        # Identifica tipo baseado na classe do ciphertext
        if isinstance(ciphertext, PreKeyWhisperMessage):
            enc_type = self.TYPE_PKMSG
        elif isinstance(ciphertext, WhisperMessage):
            enc_type = self.TYPE_MSG
        else:
            # Fallback: assume MSG
            logger.warning(f"Tipo de ciphertext desconhecido: {type(ciphertext)}, assumindo MSG")
            enc_type = self.TYPE_MSG
        
        # Serializa ciphertext
        ciphertext_bytes = ciphertext.serialize()
        
        # Cria node <enc>
        enc_node = ProtocolNode(
            tag="enc",
            attributes={
                "type": enc_type,
                "v": "2"
            },
            data=ciphertext_bytes
        )
        
        if media_type:
            enc_node.attributes["mediatype"] = media_type
        
        logger.debug(f"Mensagem individual criptografada: type={enc_type}, {len(ciphertext_bytes)} bytes")
        return enc_node
    
    async def encrypt_for_multiple_devices(
        self,
        plaintext: bytes,
        jids: list[str],
        media_type: Optional[str] = None
    ) -> list[ProtocolNode]:
        """
        Criptografa mensagem para múltiplos dispositivos.
        
        Baseado em AxolotlSendLayer.sendToContactsWithSessions().
        
        Args:
            plaintext: Dados em plaintext
            jids: Lista de JIDs de dispositivos
            media_type: Tipo de mídia (opcional)
        
        Returns:
            Lista de nodes <enc> (um para cada dispositivo)
        """
        logger.debug(f"Criptografando para {len(jids)} dispositivos")
        
        enc_nodes = []
        for jid in jids:
            try:
                enc_node = await self._encrypt_contact_message(plaintext, jid, media_type)
                enc_nodes.append(enc_node)
            except Exception as e:
                logger.error(f"Erro ao criptografar para {jid}: {e}")
                # Continua com outros dispositivos
                continue
        
        logger.debug(f"Criptografado para {len(enc_nodes)}/{len(jids)} dispositivos")
        return enc_nodes

