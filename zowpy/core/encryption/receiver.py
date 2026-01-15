"""
Encryption Receiver - Descriptografa mensagens recebidas.

Baseado no zowsuplib AxolotlReceiveLayer, mas totalmente assíncrono e moderno.
"""

from typing import Optional, Tuple, Dict, List, Callable
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...db.manager import AxolotlManager
from ...axolotl import exceptions
from ...utils.tools import WATools


class EncryptionReceiver:
    """
    Descriptografa mensagens E2E recebidas.
    
    Baseado no zowsuplib AxolotlReceiveLayer.handleEncMessage(), mas totalmente assíncrono.
    
    Suporta:
    - SKMSG: Mensagens de grupo (SenderKeyMessage)
    - PKMSG: Mensagens PreKey (PreKeyWhisperMessage)
    - MSG: Mensagens normais (WhisperMessage)
    """
    
    # Tipos de mensagem criptografada
    TYPE_SKMSG = "skmsg"
    TYPE_PKMSG = "pkmsg"
    TYPE_MSG = "msg"
    
    def __init__(
        self,
        manager: AxolotlManager,
        get_keys_fn: Optional[Callable] = None,
        process_pending_fn: Optional[Callable] = None
    ):
        """
        Inicializa receiver.
        
        Args:
            manager: AxolotlManager para descriptografia
            get_keys_fn: Função async para obter chaves (opcional)
            process_pending_fn: Função async para processar mensagens pendentes (opcional)
        """
        self._manager = manager
        self._retries: dict[str, int] = {}
        self._pending_messages: Dict[Tuple[str, Optional[str]], List[ProtocolNode]] = {}
        self._get_keys = get_keys_fn
        self._process_pending = process_pending_fn
        self._send_pkmsg_for_invalid_message = None  # Será configurado pelo client
    
    async def decrypt_message(self, node: ProtocolNode) -> Optional[bytes]:
        """
        Descriptografa mensagem E2E.
        
        Baseado em AxolotlReceiveLayer.handleEncMessage().
        
        Args:
            node: Protocol node com <enc> contendo mensagem criptografada
        
        Returns:
            bytes: Dados descriptografados (protobuf Message) ou None se erro
        
        Raises:
            exceptions.InvalidMessageException: Se mensagem inválida
            exceptions.NoSessionException: Se não há sessão
            exceptions.DuplicateMessageException: Se mensagem duplicada
        """
        # Extrai node <enc>
        enc_node = node.get_child("enc")
        if not enc_node:
            logger.warning("Mensagem sem node <enc>, não é criptografada")
            return None
        
        # Identifica tipo e versão
        enc_type = enc_node.get_attribute("type")
        enc_version = enc_node.get_attribute("v")
        enc_data = enc_node.data
        
        if not enc_data:
            logger.warning("Node <enc> sem dados")
            return None
        
        logger.debug(f"Descriptografando mensagem: type={enc_type}, version={enc_version}, data_len={len(enc_data)}")
        
        # Identifica se é grupo
        is_group = node.get_attribute("participant") is not None
        sender_jid = node.get_attribute("participant") if is_group else node.get_attribute("from")
        
        if not sender_jid:
            logger.error("Não foi possível identificar sender_jid")
            return None
        
        try:
            # Descriptografa baseado no tipo
            if enc_type == self.TYPE_SKMSG:
                # Mensagem de grupo
                return await self._decrypt_skmsg(node, enc_data, sender_jid)
            elif enc_type == self.TYPE_PKMSG:
                # Mensagem PreKey
                return await self._decrypt_pkmsg(node, enc_data, sender_jid, enc_version)
            elif enc_type == self.TYPE_MSG:
                # Mensagem normal (WhisperMessage)
                return await self._decrypt_msg(node, enc_data, sender_jid, enc_version)
            else:
                logger.warning(f"Tipo de mensagem criptografada não suportado: {enc_type}")
                return None
        
        except exceptions.InvalidKeyIdException:
            logger.warning(f"Invalid KeyId para {sender_jid}, ignorando")
            return None
        
        except exceptions.InvalidMessageException as e:
            # Trata InvalidMessage (Bad MAC, sessão desincronizada, etc.)
            error_msg = str(e) if str(e) else "Invalid message (Bad MAC ou sessão desincronizada)"
            logger.warning(f"InvalidMessage para {sender_jid}: {error_msg}")
            
            # Retry logic (máximo 2 tentativas)
            message_id = node.get_attribute("id")
            retry_count = self._retries.get(message_id, 0)
            
            if retry_count >= 2:
                logger.warning(f"InvalidMessage após 2 tentativas para {message_id}, não tentando mais")
                # TODO: Enviar PKMSG para sincronização (implementar depois)
                return None
            else:
                self._retries[message_id] = retry_count + 1
                logger.debug(f"Tentativa {retry_count + 1}/2 para mensagem {message_id}")
                # Re-tenta descriptografar (pode ter sido sincronizado)
                # Por enquanto, retorna None - retry será tratado em nível superior
                raise
        
        except exceptions.NoSessionException:
            logger.warning(f"No session para {sender_jid}, armazenando mensagem pendente")
            # Armazena mensagem pendente
            conversation_id = (node.get_attribute("from"), node.get_attribute("participant"))
            if conversation_id not in self._pending_messages:
                self._pending_messages[conversation_id] = []
            self._pending_messages[conversation_id].append(node)
            
            # Envia receipt para evitar push subsequente
            # O receipt será enviado pelo MessageProcessor se tiver ReceiptBuilder
            
            # Obtém chaves se tiver função configurada
            if self._get_keys:
                try:
                    success_jids, error_jids = await self._get_keys(sender_jid, reason="message")
                    if success_jids:
                        # Processa mensagens pendentes após obter sessão
                        if self._process_pending:
                            await self._process_pending(conversation_id[0], conversation_id[1])
                    else:
                        logger.warning(f"Erro ao obter chaves para {sender_jid}: {error_jids}")
                except Exception as e:
                    logger.error(f"Erro ao obter chaves para {sender_jid}: {e}", exc_info=True)
            else:
                logger.warning("get_keys_fn não configurada, não é possível obter chaves automaticamente")
            
            # Retorna None para indicar que mensagem está pendente
            return None
        
        except exceptions.DuplicateMessageException:
            logger.debug(f"Mensagem duplicada recebida de {sender_jid}")
            # Mensagem já foi processada, retorna None
            return None
        
        except Exception as e:
            logger.error(f"Erro inesperado ao descriptografar mensagem: {e}", exc_info=True)
            raise
    
    async def _decrypt_skmsg(
        self, 
        node: ProtocolNode, 
        enc_data: bytes, 
        sender_jid: str
    ) -> bytes:
        """
        Descriptografa mensagem SKMSG (grupo).
        
        Baseado em AxolotlReceiveLayer.handleSenderKeyMessage().
        """
        group_id = node.get_attribute("from")
        participant_id = node.get_attribute("participant") or sender_jid
        
        logger.debug(f"Descriptografando SKMSG: group={group_id}, participant={participant_id}")
        
        try:
            plaintext = await self._manager.group_decrypt(
                groupid=group_id,
                participantid=participant_id,
                data=enc_data
            )
            
            logger.debug(f"SKMSG descriptografado: {len(plaintext)} bytes")
            return plaintext
        
        except exceptions.NoSessionException:
            logger.warning(f"No session de grupo para {group_id}/{participant_id}")
            # TODO: Enviar retry
            raise
    
    async def _decrypt_pkmsg(
        self,
        node: ProtocolNode,
        enc_data: bytes,
        sender_jid: str,
        version: Optional[str]
    ) -> bytes:
        """
        Descriptografa mensagem PKMSG (PreKey).
        
        Baseado em AxolotlReceiveLayer.handlePreKeyWhisperMessage().
        """
        logger.debug(f"Descriptografando PKMSG de {sender_jid}")
        
        unpad = version == "2"
        plaintext = await self._manager.decrypt_pkmsg(
            senderid=sender_jid,
            data=enc_data,
            unpad=unpad
        )
        
        logger.debug(f"PKMSG descriptografado: {len(plaintext)} bytes")
        return plaintext
    
    async def _decrypt_msg(
        self,
        node: ProtocolNode,
        enc_data: bytes,
        sender_jid: str,
        version: Optional[str]
    ) -> bytes:
        """
        Descriptografa mensagem MSG (WhisperMessage).
        
        Baseado em AxolotlReceiveLayer.handleWhisperMessage().
        """
        logger.debug(f"Descriptografando MSG de {sender_jid}")
        
        unpad = version == "2"
        plaintext = await self._manager.decrypt_msg(
            senderid=sender_jid,
            data=enc_data,
            unpad=unpad
        )
        
        logger.debug(f"MSG descriptografado: {len(plaintext)} bytes")
        return plaintext
    
    def reset_retries(self, message_id: str) -> None:
        """
        Reseta contador de retries para uma mensagem.
        
        Args:
            message_id: ID da mensagem
        """
        if message_id in self._retries:
            del self._retries[message_id]

