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


# Enc selection: (type, version, data, mediatype)
EncSelection = Tuple[str, Optional[str], bytes, Optional[str]]


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
        self._send_retry_receipt_fn = None  # Será configurado pelo client
        self._send_receipt_on_error_fn = None  # OutgoingReceipt (delivered) em erros
        self._get_registration_id_fn = None  # Será configurado pelo client

    def _select_enc_node(self, node: ProtocolNode) -> Optional[EncSelection]:
        """
        Obtém todos os <enc> e escolhe por tipo (SKMSG / PKMSG / MSG), alinhado ao zowsup.
        Grupo: prefere SKMSG; 1:1: prefere PKMSG depois MSG.
        Retorna (type, version, data, mediatype) ou None.
        """
        enc_children = node.get_all_children("enc")
        if not enc_children:
            return None
        is_group = node.get_attribute("participant") is not None
        order = [self.TYPE_SKMSG, self.TYPE_PKMSG, self.TYPE_MSG] if is_group else [self.TYPE_PKMSG, self.TYPE_MSG]
        for enc_type in order:
            for enc_node in enc_children:
                if enc_node.get_attribute("type") == enc_type and enc_node.data:
                    version = enc_node.get_attribute("v")
                    mediatype = enc_node.get_attribute("mediatype") or enc_node.get_attribute("media_type")
                    return (enc_type, version, enc_node.data, mediatype)
        return None

    async def decrypt_message(self, node: ProtocolNode) -> Optional[Tuple[bytes, Optional[str]]]:
        """
        Descriptografa mensagem E2E.
        
        Baseado em AxolotlReceiveLayer.handleEncMessage().
        
        Args:
            node: Protocol node com <enc> contendo mensagem criptografada
        
        Returns:
            (bytes, mediatype): Dados descriptografados e mediatype do enc, ou None se erro
        
        Raises:
            exceptions.InvalidMessageException: Se mensagem inválida
            exceptions.NoSessionException: Se não há sessão
            exceptions.DuplicateMessageException: Se mensagem duplicada
        """
        selection = self._select_enc_node(node)
        if not selection:
            logger.warning("Mensagem sem node <enc> válido, não é criptografada")
            return None

        enc_type, enc_version, enc_data, enc_mediatype = selection

        logger.debug(f"Descriptografando mensagem: type={enc_type}, version={enc_version}, data_len={len(enc_data)}")
        
        # Identifica se é grupo
        is_group = node.get_attribute("participant") is not None
        sender_jid = node.get_attribute("participant") if is_group else node.get_attribute("from")
        sender_pn = node.get_attribute("sender_pn")
        
        if not sender_jid:
            logger.error("Não foi possível identificar sender_jid")
            return None


        real_target_jid = sender_jid if sender_jid else sender_pn
        
        msg_id = node.get_attribute("id")
        try:
            # Descriptografa baseado no tipo
            if enc_type == self.TYPE_SKMSG:
                out = await self._decrypt_skmsg(node, enc_data, real_target_jid)
                self.reset_retries(msg_id)
                return (out, enc_mediatype)
            elif enc_type == self.TYPE_PKMSG:
                out = await self._decrypt_pkmsg(node, enc_data, real_target_jid, enc_version)
                self.reset_retries(msg_id)
                return (out, enc_mediatype)
            elif enc_type == self.TYPE_MSG:
                out = await self._decrypt_msg(node, enc_data, real_target_jid, enc_version)
                self.reset_retries(msg_id)
                return (out, enc_mediatype)
            else:
                logger.warning(f"Tipo de mensagem criptografada não suportado: {enc_type}")
                # await self._send_receipt_for_node(node)
                return None

        except exceptions.InvalidKeyIdException:
            logger.warning(f"Invalid KeyId para {real_target_jid}, enviando receipt")
            await self._send_receipt_for_node(node)
            return None

        except exceptions.InvalidMessageException as e:
            error_msg = str(e) if str(e) else "Invalid message (Bad MAC ou sessão desincronizada)"
            logger.warning(f"InvalidMessage para {real_target_jid}: {error_msg}")
            from_jid = node.get_attribute("from")
            participant = node.get_attribute("participant")
            retry_count = self._retries.get(msg_id, 0)
            if retry_count >= 2:
                logger.warning(f"InvalidMessage após 2 tentativas para {msg_id}, enviando receipt e desistindo")
                await self._send_receipt_for_node(node)
                return None
            self._retries[msg_id] = retry_count + 1
            logger.debug(f"Enviando retry para {msg_id} (tentativa {retry_count + 1}/2)")
            reg_id = None
            if self._get_registration_id_fn:
                try:
                    reg_id = await self._get_registration_id_fn()
                except Exception:
                    pass
            t = node.get_attribute("t")
            ts = int(t) if t and str(t).isdigit() else None
            retry_entity = self.create_retry_receipt(
                message_id=msg_id,
                to=from_jid,
                retry_count=retry_count + 1,
                from_jid=node.get_attribute("to"),
                timestamp=ts,
                retry_jid=participant or from_jid,
                registration_id=reg_id,
            )
            if self._send_retry_receipt_fn:
                # await self._send_retry_receipt_fn(retry_entity)
                logger.warning(f"Retry receipt: {retry_entity}")
            else:
                logger.warning("_send_retry_receipt_fn não configurada")
            return None

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
                    import asyncio
                    async def get_keys(conversation_id: Tuple[str, str], real_target_jid: str) -> Tuple[List[str], List[str]]:
                        success_jids, error_jids  =  await self._get_keys(real_target_jid, reason=None)
                        if success_jids:
                            # Processa mensagens pendentes após obter sessão
                            if self._process_pending:
                                await self._process_pending(conversation_id[0], conversation_id[1], success_jids)
                            else:
                                logger.warning(f"Erro ao obter chaves para {real_target_jid}: {error_jids}")

                    asyncio.create_task(get_keys(conversation_id,real_target_jid))

                except Exception as e:
                    logger.error(f"Erro ao obter chaves para {real_target_jid}: {e}", exc_info=True)
                logger.warning("get_keys_fn não configurada, não é possível obter chaves automaticamente")
            
            # Retorna None para indicar que mensagem está pendente
            return None
        
        except exceptions.DuplicateMessageException:
            logger.debug(f"Mensagem duplicada recebida de {sender_jid}, enviando receipt")
            await self._send_receipt_for_node(node)
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
            # Para grupos com NoSession, também pode ser necessário sincronizar
            # Por enquanto, apenas loga - o NoSessionException será tratado no decrypt_message
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

    async def _send_receipt_for_node(self, node: ProtocolNode) -> None:
        """
        Envia OutgoingReceipt (delivered) para erros de descriptografia.
        Fluxo zowsuplib: InvalidKeyId, Duplicate, Unknown type, InvalidMessage após 2 retries.
        """
        if not self._send_receipt_on_error_fn:
            return
        message_id = node.get_attribute("id")
        from_jid = node.get_attribute("from")
        participant = node.get_attribute("participant")
        if not message_id or not from_jid:
            return
        try:
            await self._send_receipt_on_error_fn(message_id, from_jid, participant)
        except Exception as e:
            logger.error(f"Erro ao enviar receipt de erro: {e}", exc_info=True)

    def create_retry_receipt(
        self,
        message_id: str,
        to: str,
        retry_count: int = 1,
        from_jid: Optional[str] = None,
        timestamp: Optional[int] = None,
        retry_jid: Optional[str] = None,
        registration_id: Optional[int] = None
    ) -> ProtocolNode:
        """
        Cria RetryOutgoingReceiptProtocolEntity para solicitar reenvio de mensagem.
        
        Usado quando uma mensagem não pôde ser descriptografada após múltiplas tentativas
        e precisa solicitar ao remetente que reenvie a mensagem.
        
        Args:
            message_id: ID da mensagem original que precisa ser reenviada
            to: JID de destino do receipt (geralmente o remetente original)
            retry_count: Contador de retry (1, 2, 3, etc.)
            from_jid: JID de origem (opcional)
            timestamp: Timestamp da mensagem original (gerado se None)
            retry_jid: JID específico para retry (opcional, usado quando precisa enviar para device específico)
            registration_id: Registration ID do cliente (opcional, formato hex 0x...)
        
        Returns:
            RetryOutgoingReceiptProtocolEntity: Entidade de retry receipt pronta para envio
        
        Example:
            ```python
            retry_receipt = receiver.create_retry_receipt(
                message_id="MSG_ID",
                to="1234567890@s.whatsapp.net",
                retry_count=1,
                registration_id=1234567890
            )
            await client._send_protocol_node(retry_receipt)
            ```
        """
        from ...protocol.entities.receipt import RetryOutgoingReceiptProtocolEntity
        
        return RetryOutgoingReceiptProtocolEntity(
            message_id=message_id,
            to=to,
            retry_count=retry_count,
            from_jid=from_jid,
            timestamp=timestamp,
            retry_jid=retry_jid,
            registration_id=registration_id
        )

