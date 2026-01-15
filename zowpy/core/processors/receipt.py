"""
Receipt Processor - Processa receipts recebidos.
"""

from typing import Optional, Dict, Any, Callable
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter


class ReceiptProcessor(BaseProcessor):
    """Processa receipts recebidos"""
    
    def __init__(
        self,
        events: AsyncEventEmitter,
        get_enqueued_message_fn: Optional[Callable] = None,
        resend_message_fn: Optional[Callable] = None
    ):
        """
        Inicializa processor.
        
        Args:
            events: Event emitter para emitir eventos
            get_enqueued_message_fn: Função para buscar mensagem na fila (opcional)
            resend_message_fn: Função para re-enviar mensagem (opcional)
        """
        self._events = events
        self._get_enqueued_message = get_enqueued_message_fn
        self._resend_message = resend_message_fn
    
    def get_priority(self) -> int:
        """Receipts têm prioridade média"""
        return 5
    
    async def can_handle(self, node: ProtocolNode) -> bool:
        """Verifica se é um receipt"""
        return node.tag == "receipt"
    
    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa receipt.
        
        Args:
            node: Protocol node do receipt
            raw_data: Dados brutos (não usado)
        
        Returns:
            Dict com dados processados do receipt
        """
        receipt_id = node.get_attribute("id")
        receipt_type = node.get_attribute("type")
        from_jid = node.get_attribute("from")
        participant = node.get_attribute("participant")
        
        logger.debug(f"Processando receipt: id={receipt_id}, type={receipt_type}, from={from_jid}")
        
        # Processa retry receipt
        if receipt_type == "retry":
            await self._process_retry_receipt(node)
            return None  # Não emite evento genérico para retry
        
        receipt_data: Dict[str, Any] = {
            "id": receipt_id,
            "type": receipt_type,
            "from": from_jid,
            "participant": participant,
            "timestamp": node.get_attribute("t"),
        }
        
        # Emite evento
        await self._events.emit("receipt", receipt_data)
        
        return receipt_data
    
    async def _process_retry_receipt(self, node: ProtocolNode) -> None:
        """
        Processa receipt de retry.
        
        Baseado em AxolotlSendLayer.receive() para retry receipts.
        
        Quando recebe um retry receipt:
        1. Envia ACK do retry
        2. Busca mensagem original na fila
        3. Se encontrar, re-envia mensagem (pode precisar obter chaves novamente)
        """
        receipt_id = node.get_attribute("id")
        from_jid = node.get_attribute("from")
        participant = node.get_attribute("participant")
        
        logger.info(f"Recebido retry receipt: id={receipt_id}, from={from_jid}, participant={participant}")
        
        # Extrai informações de retry
        retry_count_node = node.get_child("count")
        retry_count = int(retry_count_node.data.decode()) if retry_count_node and retry_count_node.data else 0
        
        retry_jid_node = node.get_child("jid")
        retry_jid = retry_jid_node.data.decode() if retry_jid_node and retry_jid_node.data else None
        
        logger.debug(f"Retry info: count={retry_count}, jid={retry_jid}")
        
        # Envia ACK do retry (se tiver função)
        # Por enquanto, apenas loga
        
        # Busca mensagem original na fila
        if self._get_enqueued_message:
            try:
                message_node = await self._get_enqueued_message(receipt_id, keep_enqueued=True)
                
                if message_node:
                    logger.info(f"Mensagem original encontrada para retry {receipt_id}, re-enviando...")
                    
                    # Re-envia mensagem
                    if self._resend_message:
                        await self._resend_message(message_node, retry_jid, retry_count)
                    else:
                        logger.warning("resend_message_fn não configurada, não é possível re-enviar")
                else:
                    logger.warning(f"Mensagem original não encontrada na fila para retry {receipt_id}")
            except Exception as e:
                logger.error(f"Erro ao processar retry receipt: {e}", exc_info=True)
        else:
            logger.warning("get_enqueued_message_fn não configurada, não é possível processar retry")

