"""
Async WA Noise Protocol - Protocolo totalmente assíncrono.

Versão simplificada sem eventos complexos.
"""

import asyncio
from typing import Optional, Tuple
from loguru import logger

from .handshake import AsyncWAHandshake, HandshakeFailedException
from .stream import AsyncSegmentedStream
from .transport import AsyncWANoiseTransport


class AsyncWANoiseProtocol:
    """
    Protocolo totalmente assíncrono (versão simplificada).
    
    Sem eventos complexos, apenas métodos diretos.
    """

    def __init__(
        self,
        version_major: int = 6,
        version_minor: int = 3
    ):
        self._version_major = version_major
        self._version_minor = version_minor
        self._rs = None
        self._transport: Optional[AsyncWANoiseTransport] = None
        
        # Timeout de handshake
        self._handshake_timeout = 60.0
    
    @property
    def is_ready(self) -> bool:
        """Verifica se o protocolo está pronto para uso"""
        return self._transport is not None
    
    @property
    def rs(self):
        """Chave estática remota"""
        return self._rs
    
    async def start(
        self,
        stream: AsyncSegmentedStream,
        client_config,
        s,
        rs=None,
        mode=None,
        identity=None,
        regid=None,
        signedprekey=None,
        deviceid=None
    ) -> AsyncWANoiseTransport:
        """
        Inicia protocolo de forma totalmente assíncrona.
        Executa handshake e retorna transporte diretamente.
        
        Returns:
            AsyncWANoiseTransport: Transport criado após handshake
        """
        logger.info("Iniciando protocolo Noise")

        # Cria handshake
        handshake = AsyncWAHandshake(self._version_major, self._version_minor)
        if mode is not None:
            handshake.setmode(mode)
        if identity is not None:
            handshake.setIdentity(identity)
        if regid is not None:
            handshake.setRegistrationId(regid)
        if signedprekey is not None:
            handshake.setSignedPreKey(signedprekey)
        if deviceid is not None:
            handshake.setDeviceId(deviceid)

        try:
            # Executa handshake
            logger.info("Executando handshake...")
            result = await handshake.perform(client_config, stream, s, rs)

            if result is None:
                raise HandshakeFailedException("No cipherstates")

            # Cria transporte
            self._rs = handshake.rs
            self._transport = AsyncWANoiseTransport(stream, result[0], result[1])

            logger.info("Handshake concluído, transporte criado")
            return self._transport

        except Exception as e:
            logger.error(f"Erro no protocolo: {e}")
            raise
    
    async def reset(self) -> None:
        """Reseta protocolo de forma assíncrona"""
        logger.info("Resetando protocolo")
        self._transport = None
        self._rs = None
    
    async def send(self, data: bytes) -> None:
        """
        Envia dados de forma totalmente assíncrona.

        Args:
            data: Dados para enviar
        """
        if not self._transport:
            raise RuntimeError("Transport não disponível")

        await self._transport.send(data)
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        Recebe dados de forma totalmente assíncrona.

        Args:
            timeout: Timeout em segundos

        Returns:
            bytes ou None se não houver dados ou transporte indisponível
        """
        if not self._transport:
            return None

        try:
            return await self._transport.recv(timeout=timeout)
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Erro ao receber do transporte: {e}")
            return None



