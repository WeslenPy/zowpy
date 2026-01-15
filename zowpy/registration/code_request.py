"""
Async Code Request - Requisição de código assíncrona.

Refatora WACodeRequest para async usando aiohttp.
"""

import asyncio
import random
from typing import Optional, Dict, Any
from loguru import logger

try:
    import aiohttp
except ImportError:
    aiohttp = None
    logger.warning("aiohttp não disponível, funcionalidade de registration limitada")


class AsyncCodeRequest:
    """Requisição de código assíncrona."""

    def __init__(
        self,
        method: str,
        phone_number: str,
        config: Optional[Dict[str, Any]] = None,
        env: Optional[Any] = None,
    ):
        """
        :param method: Método de envio ("sms" ou "voice")
        :param phone_number: Número de telefone
        :param config: Configuração
        :param env: Ambiente (device/network)
        """
        self.method = method
        self.phone_number = phone_number
        self.config = config or {}
        self.env = env
        self.url = "https://v.whatsapp.net/v2/code"

    async def send(self) -> Dict[str, Any]:
        """
        Envia requisição de código de forma assíncrona.

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
                logger.error(f"Erro ao enviar requisição de código: {e}")
                return {"status": "fail", "reason": str(e)}

    async def _build_params(self) -> Dict[str, Any]:
        """Constrói parâmetros da requisição."""
        params = {
            "method": self.method,
            "mcc": "000",
            "mnc": "000",
            "sim_mcc": "000",
            "sim_mnc": "000",
            "reason": "",
            "cellular_strength": random.choice(["1", "2", "3", "4", "5"]),
        }

        # Adiciona parâmetros específicos do ambiente se disponível
        if self.env:
            # Parâmetros específicos do device env podem ser adicionados aqui
            pass

        return params

