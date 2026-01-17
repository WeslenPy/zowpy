"""
Async WA Noise Transport - Transport totalmente assíncrono.

Métodos send/recv totalmente assíncronos.
"""

import asyncio
from typing import Optional
from loguru import logger

from dissononce.processing.impl.cipherstate import CipherState

from .stream import AsyncSegmentedStream


class AsyncWANoiseTransport:
    """
    Transport totalmente assíncrono.
    Métodos send/recv totalmente assíncronos.
    """
    
    def __init__(
        self,
        stream: AsyncSegmentedStream,
        send_cipherstate: CipherState,
        recv_cipherstate: CipherState
    ):
        self._stream = stream
        self._send_cipherstate = send_cipherstate
        self._recv_cipherstate = recv_cipherstate
    
    async def send(self, plaintext: bytes) -> None:
        """
        Envia dados de forma totalmente assíncrona.
        Criptografia em thread pool se necessário, não bloqueia.
        
        Args:
            plaintext: Dados para enviar
        """
        # Criptografia pode ser pesada, executa em thread pool
        ciphertext = await asyncio.to_thread(
            self._send_cipherstate.encrypt_with_ad,
            b'',
            plaintext
        )
        
        # Envia - await, não bloqueia
        await self._stream.write_segment(ciphertext)
    
    async def recv(self, timeout: Optional[float] = None) -> bytearray:
        """
        Recebe dados de forma totalmente assíncrona.
        Aguarda dados, não bloqueia.
        
        Args:
            timeout: Timeout em segundos
        
        Returns:
            bytearray: Dados recebidos
        
        Raises:
            asyncio.TimeoutError: Se timeout excedido
        """
        # Recebe - await, não bloqueia
        ciphertext = await self._stream.read_segment(timeout=timeout)
        
        # Descriptografia em thread pool se necessário
        plaintext = await asyncio.to_thread(
            self._recv_cipherstate.decrypt_with_ad,
            b'',
            ciphertext
        )
        
        return bytearray(plaintext)





