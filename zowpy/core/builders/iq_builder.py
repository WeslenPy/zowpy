"""
IQ Builder - Classe base para construir IQs.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode


class IQBuilder:
    """
    Classe base para construir IQs.
    
    Fornece funcionalidades comuns para todos os tipos de IQ.
    Baseado em IqProtocolEntity do zowsuplib.
    """
    
    @staticmethod
    def generate_iq_id(id_type: int = ProtocolNode.ID_TYPE_ANDROID) -> str:
        """
        Gera ID único para IQ seguindo padrão do zowsuplib.
        
        Baseado em IqProtocolEntity._generateId() do zowsuplib.
        Por padrão usa ID_TYPE_ANDROID (32 caracteres hex aleatórios).
        
        Args:
            id_type: Tipo de ID (ProtocolNode.ID_TYPE_ANDROID ou ID_TYPE_IOS)
        
        Returns:
            String com ID único gerado
        """
        return ProtocolNode._generateId(short=True, type=id_type)
    
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

