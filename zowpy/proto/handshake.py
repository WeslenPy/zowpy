"""
Protobuf Handshake - Builder e Parser assíncronos para handshake.

Estilo whatsmeow: builders centralizados para mensagens de handshake.
"""

import asyncio
from typing import Optional, Dict, Any
from loguru import logger

from .helpers import serialize_async, deserialize_async

from ..noise.proto import wa5_pb2


class AsyncHandshakeMessageBuilder:
    """
    Builder assíncrono para mensagens de handshake.
    """
    
    @staticmethod
    async def build_client_hello(
        ephemeral: bytes,
        static: bytes,
        payload: bytes
    ) -> bytes:
        """
        Constrói ClientHello de forma assíncrona.
        
        :param ephemeral: Chave efêmera
        :param static: Chave estática
        :param payload: Payload
        :return: Bytes serializados
        """
        if wa5_pb2 is None:
            raise RuntimeError("Handshake protobuf não disponível")
        
        message = wa5_pb2.HandshakeMessage()
        client_hello = message.client_hello
        
        client_hello.ephemeral = ephemeral
        client_hello.static = static
        client_hello.payload = payload
        
        return await serialize_async(message)
    
    @staticmethod
    async def build_client_finish(
        static: bytes,
        payload: bytes
    ) -> bytes:
        """
        Constrói ClientFinish de forma assíncrona.
        
        :param static: Chave estática
        :param payload: Payload
        :return: Bytes serializados
        """
        if wa5_pb2 is None:
            raise RuntimeError("Handshake protobuf não disponível")
        
        message = wa5_pb2.HandshakeMessage()
        client_finish = message.client_finish
        
        client_finish.static = static
        client_finish.payload = payload
        
        return await serialize_async(message)


class AsyncHandshakeMessageParser:
    """
    Parser assíncrono para mensagens de handshake.
    """
    
    @staticmethod
    async def parse_server_hello(data: bytes) -> Dict[str, bytes]:
        """
        Parse ServerHello de forma assíncrona.
        
        :param data: Dados serializados
        :return: Dicionário com ephemeral, static, payload
        """
        if wa5_pb2 is None:
            raise RuntimeError("Handshake protobuf não disponível")
        
        message = await deserialize_async(data, wa5_pb2.HandshakeMessage)
        
        if not message.HasField("server_hello"):
            raise ValueError("Not a ServerHello message")
        
        server_hello = message.server_hello
        
        return {
            "ephemeral": server_hello.ephemeral,
            "static": server_hello.static,
            "payload": server_hello.payload,
        }

