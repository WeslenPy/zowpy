"""
MediaAttributes - Classe base para atributos de mídia.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_media.py
"""

from typing import Optional


class ContextInfoAttributes:
    """
    Atributos de contexto para mensagens.
    
    Representa informações de contexto como mensagens citadas, encaminhamento, etc.
    Por enquanto, implementação simplificada - pode ser expandida conforme necessário.
    """
    def __init__(self, **kwargs):
        self._stanza_id = kwargs.get("stanza_id")
        self._participant = kwargs.get("participant")
        self._quoted_message = kwargs.get("quoted_message")
        self._remote_jid = kwargs.get("remote_jid")
        self._mentioned_jid = kwargs.get("mentioned_jid", [])
        self._edit_version = kwargs.get("edit_version")
        self._revoke_message = kwargs.get("revoke_message")
        self._conversion_delay_seconds = kwargs.get("conversion_delay_seconds")
        self._forwarding_score = kwargs.get("forwarding_score")
        self._is_forwarded = kwargs.get("is_forwarded")
        self._expiration = kwargs.get("expiration")
        self._ephemeral_setting_timestamp = kwargs.get("ephemeral_setting_timestamp")
        self._external_ad_reply = kwargs.get("external_ad_reply")
        self._entry_point_conversion_source = kwargs.get("entry_point_conversion_source")
        self._entry_point_conversion_app = kwargs.get("entry_point_conversion_app")
        self._entry_point_conversion_delay_seconds = kwargs.get("entry_point_conversion_delay_seconds")
        self._disappearing_mode = kwargs.get("disappearing_mode")
        self._action_link = kwargs.get("action_link")
        self._business_message_forward_info = kwargs.get("business_message_forward_info")


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

