"""
EncryptedMessageBuilder - Constrói nodes de mensagem criptografada.

Baseado em EncryptedMessageProtocolEntity.toProtocolTreeNode() do zowsuplib.
"""

from typing import List, Optional
from loguru import logger
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
        # CORREÇÃO: Também remove qualquer <enc> direto que possa ter sido adicionado antes
        # (não deveria ter, mas remove para garantir estrutura correta)
        message_node.children = [
            child for child in message_node.children 
            if child.tag not in ["proto", "enc"]
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
            # Estrutura esperada (grupos):
            # <message>
            #   <enc type="skmsg" v="2">...</enc>  (SKMSG fora de participants, DEVE VIR PRIMEIRO)
            #   <participants>
            #     <to jid="..."><enc type="pkmsg" v="2">...</enc></to>  (sender key distribution dentro)
            #   </participants>
            # </message>
            participants_node = ProtocolNode(
                tag="participants",
                attributes={},
                children=[]
            )
            
            # Primeira passada: processa SKMSG primeiro (deve vir antes de participants)
            skmsg_entity = None
            for enc_entity in enc_entities:
                if enc_entity.tag == "enc":
                    enc_type = enc_entity.get_attribute("type")
                    if enc_type == EncEntity.TYPE_SKMSG:
                        skmsg_entity = enc_entity
                        break  # Encontrou SKMSG, processa primeiro
            
            # Adiciona SKMSG primeiro se encontrado
            if skmsg_entity:
                message_node.children.append(skmsg_entity)
            
            # Segunda passada: processa sender key distribution (vai para participants)
            for enc_entity in enc_entities:
                # Ignora SKMSG já processado
                if enc_entity == skmsg_entity:
                    continue
                
                # Se enc_entity é <to> node, adiciona ao participants (sender key distribution)
                if enc_entity.tag == "to":
                    participants_node.children.append(enc_entity)
                elif enc_entity.tag == "enc":
                    # Outros tipos de enc sem <to> wrapper não devem acontecer em mensagens normais
                    enc_type = enc_entity.get_attribute("type")
                    logger.warning(f"Enc entity tipo '{enc_type}' sem <to> wrapper em mensagem normal. Ignorando.")
                else:
                    # Outros tipos de nodes não esperados
                    logger.warning(f"Enc entity tipo '{enc_entity.tag}' não esperado em mensagem normal. Ignorando.")
            
            # Adiciona participants node se tiver children
            if participants_node.children:
                message_node.children.append(participants_node)
        
        return message_node



