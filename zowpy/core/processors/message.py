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
        send_receipt_fn=None  # Função para enviar receipt
    ):
        """
        Inicializa processor.
        
        Args:
            encryption_receiver: Receiver para descriptografar mensagens
            message_parser: Parser para parsear protobuf
            events: Event emitter para emitir eventos
            receipt_builder: Builder para criar receipts (opcional)
            send_receipt_fn: Função async para enviar receipt (opcional)
        """
        self._encryption = encryption_receiver
        self._parser = message_parser
        self._events = events
        self._receipt_builder = receipt_builder
        self._send_receipt_fn = send_receipt_fn
    
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
        
        try:
            # 1. Verifica se está criptografada
            enc_node = node.get_child("enc")
            proto_node = node.get_child("proto")
            
            if enc_node:
                # Mensagem criptografada - descriptografa
                logger.debug("Mensagem criptografada, descriptografando...")
                decrypted_bytes = await self._encryption.decrypt_message(node)
                
                if not decrypted_bytes:
                    logger.warning(f"Não foi possível descriptografar mensagem {message_id}")
                    return None
                
                # Usa bytes descriptografados para parsing
                proto_bytes = decrypted_bytes
            elif proto_node and proto_node.data:
                # Mensagem não criptografada (raro, mas possível)
                logger.debug("Mensagem não criptografada")
                proto_bytes = proto_node.data
            else:
                logger.warning(f"Mensagem sem <enc> ou <proto>: {message_id}")
                return None
            
            # 2. Parseia protobuf
            logger.debug(f"Parseando protobuf: {len(proto_bytes)} bytes")
            parsed = await self._parser.parse(proto_bytes)
            
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
            
            # 7. Envia receipt automático
            await self._send_receipt(node)
            
            return message_data
        
        except Exception as e:
            logger.error(f"Erro ao processar mensagem {message_id}: {e}", exc_info=True)
            # Não re-raise - permite que outros processors tentem
            return None
    
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
                receipt_type=self._receipt_builder.TYPE_DELIVERED,
                participant=participant
            )
            
            # Envia receipt
            await self._send_receipt_fn(receipt_node)
            logger.debug(f"Receipt automático enviado para mensagem {message_id}")
        
        except Exception as e:
            logger.error(f"Erro ao enviar receipt: {e}", exc_info=True)

