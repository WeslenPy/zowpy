"""
Async Coder - Encoder/Decoder assíncrono.

Refatora YowCoderLayer para async, sem dependência de stack.
"""

import asyncio
import zlib
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode

from ..utils.coder import WriteEncoder, ReadDecoder
from ..utils.token_dict import TokenDictionary



class AsyncEncoder:
    """Encoder assíncrono para ProtocolNode."""

    def __init__(self, token_dictionary: Any = None):
        """
        :param token_dictionary: Dicionário de tokens (opcional)
        """
        if WriteEncoder is None:
            logger.warning("WriteEncoder não disponível, funcionalidade limitada")
            self._writer = None
        else:
            if token_dictionary is None and TokenDictionary is not None:
                token_dictionary = TokenDictionary()
            self._writer = WriteEncoder(token_dictionary) if token_dictionary else None

    async def encode(self, node: ProtocolNode) -> bytes:
        """
        Codifica ProtocolNode para bytes de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        :return: Bytes codificados
        :rtype: bytes
        """
        # logger.debug(f"Encoding node: {node}")
        if self._writer is None:
            # Fallback básico
            return b""

        # Operação de codificação pode ser pesada, executa em thread pool
        return await asyncio.to_thread(
            self._writer.protocolNodeToBytes, node
        )


class AsyncDecoder:
    """Decoder assíncrono para ProtocolNode."""

    def __init__(self, token_dictionary: Any = None):
        """
        :param token_dictionary: Dicionário de tokens (opcional)
        """
        if ReadDecoder is None:
            logger.warning("ReadDecoder não disponível, funcionalidade limitada")
            self._reader = None
        else:
            if token_dictionary is None and TokenDictionary is not None:
                token_dictionary = TokenDictionary()
            self._reader = ReadDecoder(token_dictionary) if token_dictionary else None

    async def decode(self, data: bytes) -> Optional[ProtocolNode]:
        """
        Decodifica bytes para ProtocolNode de forma assíncrona.

        :param data: Dados para decodificar
        :type data: bytes
        :return: Nó do protocolo ou None
        :rtype: ProtocolNode | None
        """
        if self._reader is None:
            # Fallback básico
            return None

        # Operação de decodificação pode ser pesada, executa em thread pool
        return await asyncio.to_thread(
            self._reader.getProtocolNode, bytearray(data)
        )


class AsyncCoder:
    """
    Coder assíncrono completo (encoder + decoder).
    """

    def __init__(self, events: AsyncEventEmitter, token_dictionary: Any = None):
        """
        :param events: Emissor de eventos assíncrono
        :param token_dictionary: Dicionário de tokens (opcional)
        """
        self.events = events
        self.encoder = AsyncEncoder(token_dictionary)
        self.decoder = AsyncDecoder(token_dictionary)

    async def encode_and_send(self, node: ProtocolNode) -> None:
        """
        Codifica e envia nó de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolNode
        """
        logger.debug(f"Encoding and sending node: {node}")
        encoded = await self.encoder.encode(node)
        await self.events.emit("coder:encoded", {"data": encoded})

    async def receive_and_decode(self, data: bytes) -> Optional[ProtocolNode]:
        """
        Recebe e decodifica dados de forma assíncrona.

        :param data: Dados para decodificar
        :type data: bytes
        :return: Nó do protocolo ou None
        :rtype: ProtocolNode | None
        """
        node = await self.decoder.decode(data)
        if node:
            await self.events.emit("coder:decoded", {"node": node})
        return node

