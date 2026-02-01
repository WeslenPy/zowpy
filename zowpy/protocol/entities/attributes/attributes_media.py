"""
MediaAttributes - Classe base para atributos de mídia.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_media.py
"""

from typing import Optional

from zowpy.protocol.entities.attributes.attributes_context_info import ContextInfoAttributes


class MediaAttributes:
    """
    Classe base para atributos de mídia.
    
    Baseado em MediaAttributes do zowsuplib.
    """
    
    def __init__(self, context_info: Optional[ContextInfoAttributes] = None):
        """
        Inicializa MediaAttributes.
        
        Args:
            context_info: Informações de contexto (opcional)
        """
        if context_info:
            assert isinstance(context_info, ContextInfoAttributes), f"context_info deve ser ContextInfoAttributes, recebido: {type(context_info)}"
            self._context_info = context_info
        else:
            self._context_info = None
    
    @property
    def context_info(self) -> Optional[ContextInfoAttributes]:
        """Retorna informações de contexto."""
        return self._context_info
    
    @context_info.setter
    def context_info(self, value: Optional[ContextInfoAttributes]):
        """Define informações de contexto."""
        if value is not None:
            assert isinstance(value, ContextInfoAttributes), f"context_info deve ser ContextInfoAttributes, recebido: {type(value)}"
        self._context_info = value

