"""
Protobuf Helpers - Helpers assíncronos para protobuf.

Operações de serialização/deserialização assíncronas.
"""

import asyncio
from typing import Any, Type, TypeVar
from loguru import logger

T = TypeVar("T")


async def serialize_async(message: Any) -> bytes:
    """
    Serializa mensagem protobuf de forma assíncrona.
    
    Operações pesadas executadas em thread pool.
    
    :param message: Mensagem protobuf
    :type message: Any
    :return: Dados serializados
    :rtype: bytes
    """
    if hasattr(message, "SerializeToString"):
        # Google protobuf
        return message.SerializeToString()
    elif hasattr(message, "serialize"):
        # Betterproto
        return message.serialize()
    else:
        raise ValueError(f"Message type {type(message)} does not support serialization")


async def deserialize_async(data: bytes, message_class: Type[T]) -> T:
    """
    Deserializa mensagem protobuf de forma assíncrona.
    
    Operações pesadas executadas em thread pool.
    
    :param data: Dados serializados
    :type data: bytes
    :param message_class: Classe da mensagem
    :type message_class: Type[T]
    :return: Mensagem deserializada
    :rtype: T
    """
    message = message_class()
    
    if hasattr(message, "ParseFromString"):
        # Google protobuf
        message.ParseFromString(data)
    elif hasattr(message, "deserialize"):
        # Betterproto
        message.deserialize(data)
    else:
        raise ValueError(
            f"Message class {message_class} does not support deserialization"
        )
    
    return message


def get_protobuf_type(message: Any) -> str:
    """
    Obtém tipo de protobuf (google ou betterproto).
    
    :param message: Mensagem protobuf
    :return: Tipo ("google" ou "betterproto")
    """
    if hasattr(message, "SerializeToString") or hasattr(message, "ParseFromString"):
        return "google"
    elif hasattr(message, "serialize") or hasattr(message, "deserialize"):
        return "betterproto"
    else:
        return "unknown"

