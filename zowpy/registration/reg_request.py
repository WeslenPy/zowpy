"""
Async Reg Request - Requisição de registro assíncrona.

Refatora WARegRequest para async usando aiohttp.
"""

import asyncio
from typing import Optional, Dict, Any
from loguru import logger

try:
    import aiohttp
except ImportError:
    aiohttp = None
    logger.warning("aiohttp não disponível, funcionalidade de registration limitada")


class AsyncRegRequest:
    """Requisição de registro assíncrona."""

    def __init__(
        self,
        phone_number: str,
        code: str,
        config: Optional[Dict[str, Any]] = None,
        env: Optional[Any] = None,
    ):
        """
        :param phone_number: Número de telefone
        :param code: Código de verificação
        :param config: Configuração
        :param env: Ambiente (device/network)
        """
        self.phone_number = phone_number
        self.code = code
        self.config = config or {}
        self.env = env
        self.url = "https://v.whatsapp.net/v2/register"

    async def send(self) -> Dict[str, Any]:
        """
        Envia requisição de registro de forma assíncrona.

        :return: Resultado da requisição
        :rtype: dict
        """
        if aiohttp is None:
            raise RuntimeError("aiohttp não está disponível")

        params = await self._build_params()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.url, params=params) as response:
                    result = await response.json()
                    return result
            except Exception as e:
                logger.error(f"Erro ao enviar requisição de registro: {e}")
                return {"status": "fail", "reason": str(e)}

    async def _build_params(self) -> Dict[str, Any]:
        """Constrói parâmetros da requisição."""
        params = {
            "code": self.code,
            "mcc": "000",
            "mnc": "000",
        }

        # Adiciona parâmetros específicos do ambiente se disponível
        if self.env:
            # Parâmetros específicos do device env podem ser adicionados aqui
            pass

        return params

