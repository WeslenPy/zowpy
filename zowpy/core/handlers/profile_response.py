"""
ProfileResponse - Resposta padronizada das operações do ProfileHandler.

Substitui retorno de dicts/None/bool por um objeto com dados, mensagens de
sucesso/erro, códigos e motivo do erro.
"""

from dataclasses import dataclass
from typing import Any, Optional, List


@dataclass
class ProfileResponse:
    """
    Resposta de uma operação do ProfileHandler.

    Atributos:
        success: Se a operação foi bem-sucedida.
        data: Dados retornados (ex.: avatar info, account info, status text).
        message: Mensagem de sucesso (ex.: "Foto de perfil definida com sucesso").
        error_message: Mensagem de erro para o usuário.
        errors: Lista de mensagens de erro (detalhes).
        error_code: Código de erro principal (ex.: "404", "timeout").
        error_codes: Lista de códigos de erro quando há mais de um.
        reason: Motivo do erro (ex.: atributo "reason" do IQ).
    """

    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error_message: Optional[str] = None
    errors: Optional[List[str]] = None
    error_code: Optional[str] = None
    error_codes: Optional[List[str]] = None
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            object.__setattr__(self, "errors", [])
        if self.error_codes is None:
            object.__setattr__(
                self,
                "error_codes",
                [self.error_code] if self.error_code else [],
            )

    @classmethod
    def ok(
        cls,
        data: Optional[Any] = None,
        message: Optional[str] = None,
    ) -> "ProfileResponse":
        """Resposta de sucesso."""
        return cls(
            success=True,
            data=data,
            message=message or "Sucesso",
        )

    @classmethod
    def fail(
        cls,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        error_codes: Optional[List[str]] = None,
        reason: Optional[str] = None,
        errors: Optional[List[str]] = None,
        data: Optional[Any] = None,
    ) -> "ProfileResponse":
        """Resposta de falha."""
        codes = error_codes or ([error_code] if error_code else [])
        return cls(
            success=False,
            data=data,
            message=None,
            error_message=error_message or "Erro na operação",
            errors=errors or [],
            error_code=error_code,
            error_codes=codes if codes else None,
            reason=reason,
        )

    def to_dict(self) -> dict:
        """Converte para dict (compatibilidade com código que espera dict)."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error_message": self.error_message,
            "errors": self.errors or [],
            "error_code": self.error_code,
            "error_codes": self.error_codes or [],
            "reason": self.reason,
        }
