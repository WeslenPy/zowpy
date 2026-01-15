"""
IQ Builder - Classe base para construir IQs.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

import uuid
import time
from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode


class IQBuilder:
    """
    Classe base para construir IQs.
    
    Fornece funcionalidades comuns para todos os tipos de IQ.
    """
    
    @staticmethod
    def generate_iq_id() -> str:
        """
        Gera ID único para IQ.
        
        Returns:
            String com ID único
        """
        return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
    
    @staticmethod
    def build_base_iq(
        xmlns: str,
        iq_type: str = "get",
        iq_id: Optional[str] = None,
        to: Optional[str] = None,
        from_jid: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ base.
        
        Args:
            xmlns: XMLNS do IQ (ex: "w:g2", "usync")
            iq_type: Tipo do IQ (get, set, result, error)
            iq_id: ID do IQ (gerado se None)
            to: JID de destino (opcional)
            from_jid: JID de origem (opcional)
        
        Returns:
            ProtocolNode: Node IQ base
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        attributes = {
            "id": iq_id,
            "type": iq_type,
            "xmlns": xmlns
        }
        
        if to:
            attributes["to"] = to
        
        if from_jid:
            attributes["from"] = from_jid
        
        return ProtocolNode(
            tag="iq",
            attributes=attributes,
            children=[]
        )

