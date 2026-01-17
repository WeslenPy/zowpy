"""
Receipt Builder - Constrói receipts para mensagens.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

from typing import List, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode


class ReceiptBuilder:
    """
    Constrói receipts para mensagens.
    
    Baseado em OutgoingReceiptProtocolEntity do zowsuplib.
    
    Tipos suportados:
    - delivered: Mensagem entregue (padrão)
    - read: Mensagem lida
    - played: Mensagem reproduzida (áudio/vídeo)
    """
    
    TYPE_DELIVERED = "delivered"  # Padrão, não precisa especificar type
    TYPE_READ = "read"
    TYPE_PLAYED = "played"
    
    @staticmethod
    def build_receipt(
        message_id: str,
        from_jid: str,
        receipt_type: str = TYPE_DELIVERED,
        participant: Optional[str] = None,
        recipient: Optional[str] = None,
        call_id: Optional[str] = None,
        view: bool = False,
        server_ids: Optional[List[str]] = None
    ) -> ProtocolNode:
        """
        Constrói receipt para mensagem.
        
        Baseado em OutgoingReceiptProtocolEntity.toProtocolTreeNode()
        
        Args:
            message_id: ID da mensagem (ou lista de IDs)
            from_jid: JID do remetente (to no receipt)
            receipt_type: Tipo de receipt (delivered, read, played)
            participant: Participante (para grupos)
            recipient: Recipiente (opcional)
            call_id: ID da chamada (opcional)
            view: Se é view receipt (opcional)
            server_ids: Lista de server IDs (opcional)
        
        Returns:
            ProtocolNode: Node receipt
        """
        # Normaliza message_id para lista
        if isinstance(message_id, (list, tuple)):
            message_ids = list(message_id)
            if len(message_ids) > 1:
                receipt_id = ReceiptBuilder._generate_id()
            else:
                receipt_id = message_ids[0]
        else:
            receipt_id = message_id
            message_ids = [message_id]
        
        # Normaliza server_ids para lista
        if server_ids is not None:
            if not isinstance(server_ids, (list, tuple)):
                server_ids = [server_ids]
        else:
            server_ids = []
        
        # Cria node base
        attributes = {
            "id": receipt_id,
            "to": from_jid
        }
        
        # Adiciona type se necessário
        if receipt_type == ReceiptBuilder.TYPE_READ:
            attributes["type"] = "read"
        elif receipt_type == ReceiptBuilder.TYPE_PLAYED:
            attributes["type"] = "view"  # WhatsApp usa "view" para played
        
        # Adiciona participant se for grupo
        if participant:
            attributes["participant"] = participant
        
        # Adiciona recipient se especificado
        if recipient:
            attributes["recipient"] = recipient
        
        node = ProtocolNode(
            tag="receipt",
            attributes=attributes,
            children=[]
        )
        
        # Adiciona offer node se tiver call_id
        if call_id:
            offer_node = ProtocolNode(
                tag="offer",
                attributes={"call-id": call_id},
                children=[]
            )
            node.children.append(offer_node)
        
        # Adiciona list node se tiver múltiplas mensagens
        if len(message_ids) > 1:
            list_node = ProtocolNode(
                tag="list",
                attributes={},
                children=[]
            )
            for msg_id in message_ids:
                item_node = ProtocolNode(
                    tag="item",
                    attributes={"id": msg_id},
                    children=[]
                )
                list_node.children.append(item_node)
            node.children.append(list_node)
        
        # Adiciona list node para server_ids se houver
        if server_ids and len(server_ids) > 0:
            list_node = ProtocolNode(
                tag="list",
                attributes={},
                children=[]
            )
            for server_id in server_ids:
                item_node = ProtocolNode(
                    tag="item",
                    attributes={"server_id": server_id},
                    children=[]
                )
                list_node.children.append(item_node)
            node.children.append(list_node)
        
        logger.debug(f"Receipt construído: id={receipt_id}, type={receipt_type}, to={from_jid}")
        return node
    
    @staticmethod
    def build_ack(
        message_id: str,
        to: str,
        receipt_type: str = "ack",
        participant: Optional[str] = None,
        ack_class: str = "receipt"
    ) -> ProtocolNode:
        """
        Constrói ACK para receipt.
        
        Baseado em OutgoingAckProtocolEntity.toProtocolTreeNode()
        
        Args:
            message_id: ID da mensagem
            to: JID de destino
            receipt_type: Tipo do ACK (geralmente "ack")
            participant: Participante (para grupos)
            ack_class: Classe do ACK (geralmente "receipt")
        
        Returns:
            ProtocolNode: Node ACK
        """
        attributes = {
            "id": message_id,
            "to": to,
            "class": ack_class
        }
        
        if receipt_type:
            attributes["type"] = receipt_type
        
        if participant:
            attributes["participant"] = participant
        
        node = ProtocolNode(
            tag="ack",
            attributes=attributes,
            children=[]
        )
        
        logger.debug(f"ACK construído: id={message_id}, type={receipt_type}, to={to}")
        return node
    
    @staticmethod
    def _generate_id() -> str:
        """
        Gera ID único para receipt seguindo padrão do zowsuplib.
        
        Baseado em OutgoingReceiptProtocolEntity._generateId() do zowsuplib.
        
        Returns:
            String com ID único gerado
        """
        return ProtocolNode._generateId(type=ProtocolNode.ID_TYPE_ANDROID)

