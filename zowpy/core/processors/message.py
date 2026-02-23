"""
Message Processor - Processa mensagens recebidas.

Descriptografa, parseia e processa mensagens E2E de forma moderna e limpa.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.encryption.receiver import EncryptionReceiver
from ...core.events import AsyncEventEmitter
from ...proto.messages import AsyncMessageParser
from ...db.manager import AxolotlManager


class MessageProcessor(BaseProcessor):
    """
    Processa mensagens recebidas.
    
    Fluxo completo:
    1. Verifica se está criptografada (<enc>)
    2. Se sim, descriptografa usando EncryptionReceiver
    3. Extrai <proto> com bytes do protobuf
    4. Parseia protobuf → MessageAttributes usando AsyncMessageParser
    5. Cria estrutura de dados limpa
    6. Emite evento
    7. Envia receipt automático
    """
    
    def __init__(
        self,
        encryption_receiver: EncryptionReceiver,
        message_parser: AsyncMessageParser,
        events: AsyncEventEmitter,
        receipt_builder=None,  # Será implementado depois
        send_receipt_fn=None,  # Função para enviar receipt
        axolotl_manager: Optional[AxolotlManager] = None,
    ):
        """
        Inicializa processor.

        Args:
            encryption_receiver: Receiver para descriptografar mensagens
            message_parser: Parser para parsear protobuf
            events: Event emitter para emitir eventos
            receipt_builder: Builder para criar receipts (opcional)
            send_receipt_fn: Função async para enviar receipt (opcional)
            axolotl_manager: Manager para group_create_session (sender_key_distribution_message)
        """
        self._encryption = encryption_receiver
        self._parser = message_parser
        self._events = events
        self._receipt_builder = receipt_builder
        self._send_receipt_fn = send_receipt_fn
        self._axolotl_manager = axolotl_manager
    
    def get_priority(self) -> int:
        """Mensagens têm alta prioridade"""
        return 10
    
    async def can_handle(self, node: ProtocolNode) -> bool:
        """Verifica se é uma mensagem"""
        return node.tag == "message"
    
    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa mensagem completa.
        
        Args:
            node: Protocol node da mensagem
            raw_data: Dados brutos (não usado para mensagens, descriptografamos)
        
        Returns:
            Dict com dados processados da mensagem
        """
        from_jid = node.get_attribute("from")
        message_id = node.get_attribute("id")
        message_type = node.get_attribute("type")
        
        logger.debug(f"Processando mensagem: id={message_id}, from={from_jid}, type={message_type}")

        logger.debug(f"Node: {node}")
        
        try:
            # 1. Verifica se está criptografada
            enc_node = node.get_child("enc")
            proto_node = node.get_child("proto")

            # 7. Envia receipt automático
            await self._send_receipt(node) # marca como recebido
            
            proto_bytes = None
            enc_mediatype = None
            if enc_node:
                # Mensagem criptografada - descriptografa se raw_data não foi fornecido
                logger.debug("Mensagem criptografada, descriptografando...")
                result = await self._encryption.decrypt_message(node)
                if result is not None:
                    proto_bytes, enc_mediatype = result
            
                if not proto_bytes:
                    logger.warning(f"Não foi possível obter bytes descriptografados para mensagem {message_id}")
                    return None
            elif proto_node and proto_node.data:
                # Mensagem não criptografada (raro, mas possível)
                logger.debug("Mensagem não criptografada")
                proto_bytes = proto_node.data
            else:
                logger.warning(f"Mensagem sem <enc> ou <proto>: {message_id}")
                return None

            logger.debug(f"proto_bytes: {proto_bytes}")

            parsed = await self._parser.parse(proto_bytes)

            logger.debug(f"parsed: {parsed}")

            # E2E: tratar sender_key_distribution_message antes do parse app
            await self._handle_e2e_proto(proto_bytes, node, self._axolotl_manager)

            # 2. Parseia protobuf
            logger.debug(f"Parseando protobuf: {len(proto_bytes)} bytes")

            if not parsed:
                logger.warning(f"Falha ao parsear mensagem {message_id}")
                parsed = {}
            
            # 3. Extrai informações do node
            participant = node.get_attribute("participant")
            is_group = participant is not None
            
            # 4. Cria estrutura de dados limpa
            message_data: Dict[str, Any] = {
                "id": message_id,
                "from": from_jid,
                "to": node.get_attribute("to"),
                "type": message_type,
                "participant": participant,
                "is_group": is_group,
                "timestamp": node.get_attribute("t"),
                "notify": node.get_attribute("notify"),
            }
            if enc_mediatype is not None:
                message_data["enc_mediatype"] = enc_mediatype
            
            # 5. Adiciona dados parseados
            if parsed:
                message_data.update({
                    "message_type": parsed.get("type", "unknown"),
                    "text": parsed.get("text", ""),
                    "data": parsed.get("data"),
                })
            
            # 6. Emite evento
            logger.info(f"Mensagem processada: id={message_id}, from={from_jid}, text={message_data.get('text', '')[:50]}")
            await self._events.emit("message", message_data)
      
            
            return message_data
        
        except Exception as e:
            logger.exception(e)
            logger.error(f"Erro ao processar mensagem {message_id}: {e}", exc_info=True)
            # Não re-raise - permite que outros processors tentem
            return None
    
    async def _handle_e2e_proto(
        self,
        proto_bytes: bytes,
        node: ProtocolNode,
        manager: Optional[AxolotlManager],
    ) -> None:
        """
        Parse do proto E2E; se sender_key_distribution_message, chama group_create_session.
        Alinhado ao zowsup parseAndHandleMessageProto.
        """
        if not manager:
            return
        try:
            m = await self._parser.bytes_to_proto(proto_bytes)

            if not m.HasField("sender_key_distribution_message"):
                return
            sk = m.sender_key_distribution_message
            if not sk.axolotl_sender_key_distribution_message:
                return
            group_id = node.get_attribute("from")
            participant_id = node.get_attribute("participant") or group_id
            if not group_id:
                return
            skmsgdata = sk.axolotl_sender_key_distribution_message
            await manager.group_create_session(group_id, participant_id, skmsgdata)
            logger.debug(f"group_create_session: group={group_id}, participant={participant_id}")
        except Exception as e:
            logger.debug(f"_handle_e2e_proto: {e}")
    
    async def _send_receipt(self, node: ProtocolNode) -> None:
        """
        Envia receipt automático para mensagem recebida.
        
        Args:
            node: Protocol node da mensagem
        """
        if not self._receipt_builder or not self._send_receipt_fn:
            return
        
        try:
            message_id = node.get_attribute("id")
            from_jid = node.get_attribute("from")
            participant = node.get_attribute("participant")
            
            # Cria receipt usando ReceiptBuilder
            receipt_node = self._receipt_builder.build_receipt(
                message_id=message_id,
                from_jid=from_jid,
                receipt_type=None,
                participant=participant
            )
            
            # Envia receipt
            await self._send_receipt_fn(receipt_node)
            logger.debug(f"Receipt automático enviado para mensagem {message_id}")
        
        except Exception as e:
            logger.error(f"Erro ao enviar receipt: {e}", exc_info=True)
