"""
Receipt Protocol Entities - Entidades de receipt e ack.

Baseado em ReceiptProtocolEntity e AckProtocolEntity do zowsuplib.
"""

import time
import binascii
from typing import Optional, List
from .base import ProtocolEntity


class ReceiptProtocolEntity(ProtocolEntity):
    """
    Entidade de receipt <receipt>.
    
    Baseado em ReceiptProtocolEntity do zowsuplib.
    """
    
    TYPE_DELIVERED = "delivered"
    TYPE_READ = "read"
    
    def __init__(
        self,
        receipt_type: str,
        message_ids: List[str],
        to: Optional[str] = None,
        from_jid: Optional[str] = None,
        receipt_id: Optional[str] = None
    ):
        """
        Cria entidade de receipt.
        
        Args:
            receipt_type: Tipo de receipt (delivered, read)
            message_ids: Lista de IDs de mensagens
            to: JID de destino (opcional)
            from_jid: JID de origem (opcional)
            receipt_id: ID do receipt (gerado se None)
        """
        if not receipt_id:
            receipt_id = self._generate_id()
        
        attributes = {
            "type": receipt_type,
            "id": receipt_id
        }
        
        if to:
            attributes["to"] = to
        
        if from_jid:
            attributes["from"] = from_jid
        
        children = []
        for msg_id in message_ids:
            child = ProtocolEntity(
                tag="item",
                attributes={"id": msg_id}
            )
            children.append(child)
        
        super().__init__(
            tag="receipt",
            attributes=attributes,
            children=children
        )
        
        self.receipt_type = receipt_type
        self.message_ids = message_ids
        self.receipt_id = receipt_id


class RetryOutgoingReceiptProtocolEntity(ProtocolEntity):
    """
    Entidade de receipt de retry <receipt type="retry">.
    
    Usado quando uma mensagem precisa ser reenviada devido a erro.
    Baseado em RetryOutgoingReceiptProtocolEntity do zowsuplib.
    
    Formato:
    <receipt type="retry" id="..." to="..." from="...">
      <retry count="1" t="..." id="..." v="1"/>
      <jid>...</jid> (opcional)
      <registration>...</registration> (opcional, bytes hex)
    </receipt>
    """
    
    @staticmethod
    def _int_to_bytes(val: int) -> bytes:
        """
        Converte inteiro para bytes hexadecimais.
        
        Baseado em ResultGetKeysIqProtocolEntity._intToBytes() do zowsuplib.
        
        Args:
            val: Valor inteiro (ex: 0x6a2d5d7c ou 1782107484)
        
        Returns:
            bytes: Bytes binários (ex: b'\\x6a\\x2d\\x5d\\x7c')
        
        Example:
            >>> _int_to_bytes(0x6a2d5d7c)
            b'\\x6a\\x2d\\x5d\\x7c'
        """
        return binascii.unhexlify(format(val, 'x').zfill(8).encode())
    
    def __init__(
        self,
        message_id: str,
        to: str,
        retry_count: int = 1,
        from_jid: Optional[str] = None,
        timestamp: Optional[int] = None,
        retry_jid: Optional[str] = None,
        registration_id: Optional[int] = None,
        receipt_id: Optional[str] = None
    ):
        """
        Cria entidade de receipt de retry.
        
        Baseado em RetryOutgoingReceiptProtocolEntity.toProtocolTreeNode() do zowsuplib.
        
        Args:
            message_id: ID da mensagem original que será reenviada
            to: JID de destino do receipt (geralmente o remetente original)
            retry_count: Contador de retry (1, 2, 3, etc.)
            from_jid: JID de origem (opcional)
            timestamp: Timestamp da mensagem original (gerado se None)
            retry_jid: JID específico para retry (opcional, usado quando precisa enviar para device específico)
            registration_id: Registration ID do cliente (opcional, inteiro que será convertido para bytes hex)
            receipt_id: ID do receipt (gerado se None, geralmente usa message_id)
        """
        if not receipt_id:
            receipt_id = message_id
        
        if timestamp is None:
            timestamp = int(time.time())
        
        attributes = {
            "type": "retry",
            "id": receipt_id,
            "to": to
        }
        
        if from_jid:
            attributes["from"] = from_jid
        
        # Cria node <retry> com informações do retry
        retry_attributes = {
            "count": str(retry_count),
            "t": str(timestamp),
            "id": message_id,
            "v": "1"
        }
        retry_node = ProtocolEntity(
            tag="retry",
            attributes=retry_attributes
        )
        
        children = [retry_node]
        
        # Adiciona node <jid> se retry_jid fornecido
        if retry_jid:
            jid_node = ProtocolEntity(
                tag="jid",
                data=retry_jid.encode() if isinstance(retry_jid, str) else retry_jid
            )
            children.append(jid_node)
        
        # Adiciona node <registration> se registration_id fornecido
        # Baseado em zowsuplib: ResultGetKeysIqProtocolEntity._intToBytes()
        # Converte inteiro para bytes binários hexadecimais (não string com 0x)
        if registration_id is not None:
            reg_bytes = self._int_to_bytes(registration_id)
            reg_node = ProtocolEntity(
                tag="registration",
                data=reg_bytes
            )
            children.append(reg_node)
        
        super().__init__(
            tag="receipt",
            attributes=attributes,
            children=children
        )
        
        self.message_id = message_id
        self.retry_count = retry_count
        self.timestamp = timestamp
        self.retry_jid = retry_jid
        self.registration_id = registration_id
        self.receipt_id = receipt_id
