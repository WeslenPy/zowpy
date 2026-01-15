"""
Yowsup Config - Porta configuração do yowsup.

Porta lógica de configuração do yowsup mantendo estrutura.
"""

from typing import Optional, Dict, Any
from loguru import logger


class YowsupConfig:
    """
    Configuração do Yowsup portada.
    Mantém compatibilidade com estrutura original.
    """

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        :param config_data: Dados de configuração
        """
        self._config = config_data or {}
        self._id: Optional[str] = None
        self._login: Optional[str] = None
        self._phone: Optional[str] = None

    @property
    def id(self) -> Optional[str]:
        """ID da configuração."""
        return self._id or self._config.get("id")

    @id.setter
    def id(self, value: str) -> None:
        """Define ID da configuração."""
        self._id = value
        self._config["id"] = value

    @property
    def login(self) -> Optional[str]:
        """Login (username)."""
        return self._login or self._config.get("login")

    @login.setter
    def login(self, value: str) -> None:
        """Define login."""
        self._login = value
        self._config["login"] = value

    @property
    def phone(self) -> Optional[str]:
        """Número de telefone."""
        return self._phone or self._config.get("phone")

    @phone.setter
    def phone(self, value: str) -> None:
        """Define número de telefone."""
        self._phone = value
        self._config["phone"] = value

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return self._config.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YowsupConfig":
        """Cria a partir de dicionário."""
        return cls(data)

