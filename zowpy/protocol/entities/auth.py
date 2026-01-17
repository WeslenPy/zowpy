"""
Auth Protocol Entities - Entidades de autenticação.

Baseado em AuthProtocolEntity, ChallengeProtocolEntity, ResponseProtocolEntity do zowsuplib.
"""

from typing import Optional
from .base import ProtocolEntity


class AuthProtocolEntity(ProtocolEntity):
    """
    Entidade de autenticação <auth>.
    
    Baseado em AuthProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        mechanism: str = "WAUTH-2",
        user: Optional[str] = None,
        passive: str = "false",
        data: Optional[bytes] = None
    ):
        """
        Cria entidade de autenticação.
        
        Args:
            mechanism: Mecanismo de autenticação (padrão: WAUTH-2)
            user: Username (número de telefone)
            passive: Se é conexão passiva (padrão: false)
            data: Dados adicionais (nonce, etc.)
        """
        attributes = {
            "mechanism": mechanism,
            "passive": passive
        }
        
        if user:
            attributes["user"] = user
        
        super().__init__(
            tag="auth",
            attributes=attributes,
            data=data
        )


class ChallengeProtocolEntity(ProtocolEntity):
    """
    Entidade de challenge <challenge>.
    
    Baseado em ChallengeProtocolEntity do zowsuplib.
    """
    
    def __init__(self, challenge_data: bytes):
        """
        Cria entidade de challenge.
        
        Args:
            challenge_data: Dados do challenge (bytes)
        """
        super().__init__(
            tag="challenge",
            data=challenge_data
        )


class ResponseProtocolEntity(ProtocolEntity):
    """
    Entidade de response <response>.
    
    Baseado em ResponseProtocolEntity do zowsuplib.
    """
    
    def __init__(self, response_data: bytes):
        """
        Cria entidade de response.
        
        Args:
            response_data: Dados da resposta (bytes)
        """
        super().__init__(
            tag="response",
            data=response_data
        )

