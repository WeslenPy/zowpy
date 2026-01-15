"""
Notification Processor - Processa notifications recebidos.
"""

from typing import Optional, Dict, Any, Callable
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter


class NotificationProcessor(BaseProcessor):
    """Processa notifications recebidos"""
    
    def __init__(
        self,
        events: AsyncEventEmitter,
        flush_prekeys_fn: Optional[Callable] = None,
        get_keys_fn: Optional[Callable] = None,
        send_ack_fn: Optional[Callable] = None
    ):
        """
        Inicializa processor.
        
        Args:
            events: Event emitter para emitir eventos
            flush_prekeys_fn: Função async para enviar prekeys (opcional)
            get_keys_fn: Função async para obter chaves (opcional)
            send_ack_fn: Função async para enviar ACK (opcional)
        """
        self._events = events
        self._flush_prekeys = flush_prekeys_fn
        self._get_keys = get_keys_fn
        self._send_ack = send_ack_fn
    
    def get_priority(self) -> int:
        """Notifications têm prioridade média"""
        return 5
    
    async def can_handle(self, node: ProtocolNode) -> bool:
        """Verifica se é uma notification"""
        return node.tag == "notification"
    
    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa notification.
        
        Args:
            node: Protocol node da notification
            raw_data: Dados brutos (não usado)
        
        Returns:
            Dict com dados processados da notification
        """
        notification_id = node.get_attribute("id")
        notification_type = node.get_attribute("type")
        from_jid = node.get_attribute("from")
        
        logger.debug(f"Processando notification: id={notification_id}, type={notification_type}, from={from_jid}")
        
        # Processa notificações de encrypt
        if notification_type == "encrypt":
            await self._process_encrypt_notification(node)
            return None  # Não emite evento genérico para encrypt notifications
        
        notification_data: Dict[str, Any] = {
            "id": notification_id,
            "type": notification_type,
            "from": from_jid,
            "timestamp": node.get_attribute("t"),
        }
        
        # Emite evento
        await self._events.emit("notification", notification_data)
        
        return notification_data
    
    async def _process_encrypt_notification(self, node: ProtocolNode) -> None:
        """
        Processa notificação de encrypt.
        
        Baseado em AxolotlControlLayer.onRequestKeysEncryptNotification() e
        onIdentityChangeEncryptNotification()
        
        Tipos:
        - RequestKeysEncryptNotification: Tem <count> → envia prekeys
        - IdentityChangeEncryptNotification: Tem <identity> → obtém chaves do remetente
        """
        notification_id = node.get_attribute("id")
        from_jid = node.get_attribute("from")
        
        # Envia ACK primeiro
        if self._send_ack:
            try:
                await self._send_ack(notification_id, "notification", "encrypt", from_jid)
            except Exception as e:
                logger.error(f"Erro ao enviar ACK de notification: {e}")
        
        # Verifica tipo de notification
        count_node = node.get_child("count")
        identity_node = node.get_child("identity")
        
        if count_node:
            # RequestKeysEncryptNotification - servidor pede para enviar prekeys
            logger.info("Recebida RequestKeysEncryptNotification, enviando prekeys...")
            if self._flush_prekeys:
                try:
                    # Obtém signed_prekey e prekeys não enviadas
                    # Por enquanto, apenas loga - a implementação completa requer acesso ao client
                    logger.debug("RequestKeysEncryptNotification processada (flush_prekeys será chamado pelo client)")
                    # O client deve chamar _check_and_flush_prekeys() quando receber esta notification
                except Exception as e:
                    logger.error(f"Erro ao processar RequestKeysEncryptNotification: {e}")
            else:
                logger.warning("RequestKeysEncryptNotification recebida, mas flush_prekeys_fn não está configurada")
        
        elif identity_node:
            # IdentityChangeEncryptNotification - identidade do remetente mudou
            logger.info(f"Recebida IdentityChangeEncryptNotification de {from_jid}, obtendo chaves...")
            if self._get_keys:
                try:
                    # Obtém chaves do remetente
                    success_jids, error_jids = await self._get_keys(from_jid)
                    if error_jids:
                        logger.warning(f"Erros ao obter chaves após mudança de identidade: {error_jids}")
                    else:
                        logger.info(f"Chaves obtidas com sucesso para {from_jid}")
                except Exception as e:
                    logger.error(f"Erro ao processar IdentityChangeEncryptNotification: {e}")
            else:
                logger.warning("IdentityChangeEncryptNotification recebida, mas get_keys_fn não está configurada")
        
        else:
            logger.debug(f"Notification encrypt sem <count> ou <identity>, ignorando")

