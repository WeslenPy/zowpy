"""
Contact Builder - Constrói IQs para operações de contatos.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

import time
from typing import List, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from .iq_builder import IQBuilder


class ContactBuilder:
    """
    Constrói IQs para operações de contatos.
    
    Baseado nos protocol entities do zowsuplib:
    - SyncIqProtocolEntity
    - GetSyncIqProtocolEntity
    - DevicesGetSyncIqProtocolEntity
    """
    
    # Constantes
    XMLNS_SYNC = "usync"
    MODE_FULL = "full"
    MODE_DELTA = "delta"
    CONTEXT_REGISTRATION = "registration"
    CONTEXT_INTERACTIVE = "interactive"
    
    @staticmethod
    def _generate_sid() -> str:
        """
        Gera SID único para sync.
        
        Returns:
            String com SID
        """
        # Baseado em: str((int(time.time()) + 11644477200) * 10000000)
        return str((int(time.time()) + 11644477200) * 10000000)
    
    @staticmethod
    def build_sync_contacts(
        numbers: List[str],
        mode: str = MODE_FULL,
        context: str = CONTEXT_INTERACTIVE,
        sid: Optional[str] = None,
        index: int = 0,
        last: bool = True,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para sincronizar contatos.
        
        Baseado em GetSyncIqProtocolEntity.
        
        Args:
            numbers: Lista de números de telefone (com ou sem +)
            mode: Modo de sync (full ou delta)
            context: Contexto (registration ou interactive)
            sid: SID do sync (gerado se None)
            index: Índice do sync
            last: Se é o último chunk
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para sincronizar contatos
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        if not sid:
            sid = ContactBuilder._generate_sid()
        
        # Cria node base
        node = IQBuilder.build_base_iq(
            xmlns=ContactBuilder.XMLNS_SYNC,
            iq_type="get",
            iq_id=iq_id
        )
        
        # Cria node <usync>
        usync_attrs = {
            "sid": sid,
            "index": str(index),
            "last": "true" if last else "false",
            "mode": mode,
            "context": context
        }
        
        usync_node = ProtocolNode(
            tag="usync",
            attributes=usync_attrs,
            children=[]
        )
        
        # Adiciona node <query> com subnodes
        query_node = ProtocolNode(
            tag="query",
            attributes={},
            children=[
                ProtocolNode(tag="lid", attributes={}, children=[]),
                ProtocolNode(tag="status", attributes={}, children=[]),
                ProtocolNode(tag="contact", attributes={}, children=[])
            ]
        )
        usync_node.children.append(query_node)
        
        # Adiciona node <list> com números
        list_node = ProtocolNode(
            tag="list",
            attributes={},
            children=[]
        )
        
        for number in numbers:
            # Garante que número começa com +
            if not number.startswith("+"):
                number = "+" + number
            
            # Cria estrutura: <user><contact>number</contact></user>
            contact_node = ProtocolNode(
                tag="contact",
                attributes={},
                data=number.encode("utf-8")
            )
            user_node = ProtocolNode(
                tag="user",
                attributes={},
                children=[contact_node]
            )
            list_node.children.append(user_node)
        
        usync_node.children.append(list_node)
        node.children.append(usync_node)
        
        logger.debug(f"Contact sync IQ construído: numbers={len(numbers)}, mode={mode}, context={context}")

        logger.debug(f"Contact sync IQ construído: {node}")
        return node
    
    @staticmethod
    def build_sync_devices(
        jids: List[str],
        mode: str = MODE_FULL,
        context: str = CONTEXT_INTERACTIVE,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para sincronizar dispositivos de contatos.
        
        Baseado em DevicesGetSyncIqProtocolEntity.
        
        Args:
            jids: Lista de JIDs dos contatos
            mode: Modo de sync (full ou delta)
            context: Contexto (registration ou interactive)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para sincronizar dispositivos
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        # Cria node base
        node = IQBuilder.build_base_iq(
            xmlns=ContactBuilder.XMLNS_SYNC,
            iq_type="get",
            iq_id=iq_id
        )
        
        # Cria node <usync>
        usync_attrs = {
            "mode": mode,
            "context": context
        }
        
        usync_node = ProtocolNode(
            tag="usync",
            attributes=usync_attrs,
            children=[]
        )
        
        # Adiciona node <query> com subnodes
        # CORREÇÃO: Baseado em DevicesGetSyncIqProtocolEntity.toProtocolTreeNode()
        # O query deve ter <lid> e <devices version="2"> (não status e contact)
        query_node = ProtocolNode(
            tag="query",
            attributes={},
            children=[
                ProtocolNode(tag="lid", attributes={}, children=[]),
                ProtocolNode(tag="devices", attributes={"version": "2"}, children=[])
            ]
        )
        usync_node.children.append(query_node)
        
        # Adiciona node <list> com JIDs
        list_node = ProtocolNode(
            tag="list",
            attributes={},
            children=[]
        )
        
        for jid in jids:
            # CORREÇÃO: Formato correto baseado em DevicesGetSyncIqProtocolEntity.toProtocolTreeNode()
            # O zowsuplib usa <user jid="..."> com JID completo
            # Se o jid for apenas número, precisa converter para JID completo
            if "@" in jid:
                # JID completo: usa como atributo jid diretamente
                user_jid = jid
            else:
                # Apenas número: converte para JID completo
                # Remove device_id se existir (ex: "559885700260:0" -> "559885700260")
                number = jid.split(":")[0] if ":" in jid else jid
                user_jid = f"{number}@s.whatsapp.net"
            
            # Usa formato do zowsuplib: <user jid="...">
            user_node = ProtocolNode(
                tag="user",
                attributes={"jid": user_jid},
                children=[]
            )
            list_node.children.append(user_node)
        
        usync_node.children.append(list_node)
        node.children.append(usync_node)
        
        logger.debug(f"Device sync IQ construído: jids={len(jids)}, mode={mode}, context={context}")
        return node

