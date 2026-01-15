"""
Protobuf Utilities - Utilitários para Protobuf.

Wrapper para compatibilidade com código legado.
Recomenda-se usar zowpy.proto.helpers diretamente.
"""

from typing import Any, Optional
import asyncio

# Importa helpers assíncronos
try:
    from ..proto.helpers import serialize_async, deserialize_async
except ImportError:
    serialize_async = None
    deserialize_async = None


def serialize_message(message: Any) -> bytes:
    """
    Serializa mensagem protobuf (síncrono, para compatibilidade).
    
    Para código novo, use serialize_async().
    
    Args:
        message: Mensagem protobuf
    
    Returns:
        bytes: Dados serializados
    """
    if hasattr(message, 'SerializeToString'):
        return message.SerializeToString()
    elif hasattr(message, 'serialize'):
        return message.serialize()
    else:
        raise ValueError("Message does not support serialization")


def deserialize_message(data: bytes, message_class: type) -> Any:
    """
    Deserializa mensagem protobuf (síncrono, para compatibilidade).
    
    Para código novo, use deserialize_async().
    
    Args:
        data: Dados serializados
        message_class: Classe da mensagem
    
    Returns:
        Mensagem deserializada
    """
    message = message_class()
    if hasattr(message, 'ParseFromString'):
        message.ParseFromString(data)
    elif hasattr(message, 'deserialize'):
        message.deserialize(data)
    else:
        raise ValueError("Message class does not support deserialization")
    
    return message


async def serialize_message_async(message: Any) -> bytes:
    """
    Serializa mensagem protobuf de forma assíncrona.
    
    Wrapper para serialize_async do proto.helpers.
    
    Args:
        message: Mensagem protobuf
    
    Returns:
        bytes: Dados serializados
    """
    if serialize_async is None:
        # Fallback síncrono
        return serialize_message(message)
    return await serialize_async(message)


async def deserialize_message_async(data: bytes, message_class: type) -> Any:
    """
    Deserializa mensagem protobuf de forma assíncrona.
    
    Wrapper para deserialize_async do proto.helpers.
    
    Args:
        data: Dados serializados
        message_class: Classe da mensagem
    
    Returns:
        Mensagem deserializada
    """
    if deserialize_async is None:
        # Fallback síncrono
        return deserialize_message(data, message_class)
    return await deserialize_async(data, message_class)

