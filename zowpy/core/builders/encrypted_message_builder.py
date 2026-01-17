"""
EncryptedMessageBuilder - Constrói nodes de mensagem criptografada.

Baseado em EncryptedMessageProtocolEntity.toProtocolTreeNode() do zowsuplib.
"""

from typing import List, Optional
from ...protocol.structs import ProtocolNode
from .enc_entity import EncEntity


class EncryptedMessageBuilder:
    """
    Builder para criar nodes de mensagem criptografada.
    
    Baseado em zowsuplib.yowsup.layers.axolotl.protocolentities.message_encrypted.EncryptedMessageProtocolEntity
    """
    
    @staticmethod
    def build_encrypted_message(
        message_node: ProtocolNode,
        enc_entities: List[ProtocolNode],
        participant: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói node de mensagem criptografada seguindo padrão do zowsuplib.
        
        Baseado em EncryptedMessageProtocolEntity.toProtocolTreeNode()
        
        Estrutura:
        - Peer message: <message><meta><enc>...</enc></message>
        - Normal message: <message><enc>...</enc><participants><to>...</to></participants></message>
        
        Args:
            message_node: Node base da mensagem (com atributos to, from, type, id, etc.)
            enc_entities: Lista de nodes <enc> ou <to> com <enc>
            participant: JID do participante (opcional, usado para retry)
        
        Returns:
            ProtocolNode: Node de mensagem criptografada completo
        """
        # Copia biz node se existir (será adicionado depois em _add_message_extras)
        # Baseado em AxolotlSendLayer.sendEncEntities() linha 197-199
        biz_node = message_node.get_child("biz")
        
        # Remove <proto> node se existir (não deve estar no node final)
        message_node.children = [
            child for child in message_node.children 
            if child.tag != "proto"
        ]
        
        # Adiciona biz node de volta se existir (será processado em _add_message_extras)
        if biz_node:
            message_node.children.append(biz_node)
        
        # Obtém category para determinar estrutura
        category = message_node.get_attribute("category")
        
        if category == "peer":
            # Peer message: estrutura simples com <meta>
            # Baseado em EncryptedMessageProtocolEntity.toProtocolTreeNode() linha 34-38
            if enc_entities:
                # Adiciona <meta> node
                meta_node = ProtocolNode(
                    tag="meta",
                    attributes={"appdata": "default"}
                )
                message_node.children.append(meta_node)
                
                # Adiciona primeiro enc entity
                message_node.children.append(enc_entities[0])
        else:
            # Normal message: estrutura com participants node
            # Baseado em EncryptedMessageProtocolEntity.toProtocolTreeNode() linha 40-50
            participants_node = ProtocolNode(
                tag="participants",
                attributes={},
                children=[]
            )
            
            for enc_entity in enc_entities:
                # Se enc_entity é <to> node, adiciona ao participants
                if enc_entity.tag == "to":
                    participants_node.children.append(enc_entity)
                else:
                    # Se é <enc> direto, adiciona ao message node
                    message_node.children.append(enc_entity)
            
            # Adiciona participants node se tiver children
            if participants_node.children:
                message_node.children.append(participants_node)
        
        return message_node



