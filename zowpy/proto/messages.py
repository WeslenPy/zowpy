"""
Protobuf Messages - Builder e Parser assíncronos para mensagens.

Estilo whatsmeow: builders e parsers centralizados e assíncronos.
"""

import asyncio
from typing import Optional, Dict, Any, List
from enum import IntEnum
from dataclasses import dataclass
from loguru import logger

from zowpy.protocol.entities.attributes.converter import AttributesConverter

from .helpers import serialize_async, deserialize_async

# Imports condicionais para protobuf
from .e2e_pb2 import Message as E2EMessage
# wa_struct_pb2 não tem Message, apenas HandshakeMessage e ClientPayload

WAStructMessage = None  # Não disponível neste protobuf


class MessageType(IntEnum):
    """Tipos de mensagem."""
    TEXT = 1
    IMAGE = 2
    VIDEO = 3
    AUDIO = 4
    DOCUMENT = 5
    STICKER = 14
    LOCATION = 15
    CONTACT = 16
    BUTTONS = 6
    LIST = 7
    URL = 8
    BUTTONS_RESPONSE = 9
    LIST_RESPONSE = 10
    PRODUCT = 11
    POLL = 12
    POLL_RESPONSE = 13
    REACTION = 15
    OTHER = 99


@dataclass
class TextMessage:
    """Mensagem de texto."""
    text: str
    context_info: Optional[Dict[str, Any]] = None


@dataclass
class ImageMessage:
    """Mensagem de imagem."""
    url: str
    mimetype: str
    caption: Optional[str] = None
    file_sha256: Optional[bytes] = None
    file_length: Optional[int] = None
    height: Optional[int] = None
    width: Optional[int] = None
    media_key: Optional[bytes] = None
    jpeg_thumbnail: Optional[bytes] = None


@dataclass
class VideoMessage:
    """Mensagem de vídeo."""
    url: str
    mimetype: str
    caption: Optional[str] = None
    file_sha256: Optional[bytes] = None
    file_length: Optional[int] = None
    duration: Optional[int] = None
    height: Optional[int] = None
    width: Optional[int] = None
    media_key: Optional[bytes] = None
    jpeg_thumbnail: Optional[bytes] = None


@dataclass
class AudioMessage:
    """Mensagem de áudio."""
    url: str
    mimetype: str
    file_sha256: Optional[bytes] = None
    file_length: Optional[int] = None
    duration: Optional[int] = None
    ptt: bool = False
    media_key: Optional[bytes] = None


@dataclass
class DocumentMessage:
    """Mensagem de documento."""
    url: str
    mimetype: str
    title: Optional[str] = None
    file_sha256: Optional[bytes] = None
    file_length: Optional[int] = None
    page_count: Optional[int] = None
    media_key: Optional[bytes] = None
    filename: Optional[str] = None


class AsyncMessageBuilder:
    """
    Builder assíncrono para mensagens protobuf.
    Estilo whatsmeow: métodos de construção centralizados.
    """
    
    @staticmethod
    async def build_text(text: str, context_info: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Constrói mensagem de texto.
        
        :param text: Texto da mensagem
        :param context_info: Informações de contexto
        :return: Bytes da mensagem serializada
        """
        if E2EMessage is None:
            raise RuntimeError("E2EMessage não disponível")
        
        # Cria mensagem protobuf
        message = E2EMessage()
        message.conversation = text
        
        # Adiciona contexto se fornecido
        if context_info:
            # Processa contexto (pode ser pesado)
            pass
        
        return await serialize_async(message)
    
    @staticmethod
    async def build_image(
        url: str,
        mimetype: str,
        caption: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Constrói mensagem de imagem.
        
        :param url: URL da imagem
        :param mimetype: Tipo MIME
        :param caption: Legenda
        :param kwargs: Outros parâmetros
        :return: Bytes da mensagem serializada
        """
        if E2EMessage is None:
            raise RuntimeError("E2EMessage não disponível")
        
        message = E2EMessage()
        image = message.image_message
        
        image.url = url
        image.mimetype = mimetype
        
        if caption:
            image.caption = caption
        if "file_sha256" in kwargs:
            image.file_sha256 = kwargs["file_sha256"]
        if "file_length" in kwargs:
            image.file_length = kwargs["file_length"]
        if "height" in kwargs:
            image.height = kwargs["height"]
        if "width" in kwargs:
            image.width = kwargs["width"]
        if "media_key" in kwargs:
            image.media_key = kwargs["media_key"]
        if "jpeg_thumbnail" in kwargs:
            image.jpeg_thumbnail = kwargs["jpeg_thumbnail"]
        
        return await serialize_async(message)
    
    @staticmethod
    async def build_video(
        url: str,
        mimetype: str,
        caption: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Constrói mensagem de vídeo.
        
        :param url: URL do vídeo
        :param mimetype: Tipo MIME
        :param caption: Legenda
        :param kwargs: Outros parâmetros
        :return: Bytes da mensagem serializada
        """
        if E2EMessage is None:
            raise RuntimeError("E2EMessage não disponível")
        
        message = E2EMessage()
        video = message.video_message
        
        video.url = url
        video.mimetype = mimetype
        
        if caption:
            video.caption = caption
        if "file_sha256" in kwargs:
            video.file_sha256 = kwargs["file_sha256"]
        if "file_length" in kwargs:
            video.file_length = kwargs["file_length"]
        if "duration" in kwargs:
            video.seconds = kwargs["duration"]
        if "height" in kwargs:
            video.height = kwargs["height"]
        if "width" in kwargs:
            video.width = kwargs["width"]
        if "media_key" in kwargs:
            video.media_key = kwargs["media_key"]
        if "jpeg_thumbnail" in kwargs:
            video.jpeg_thumbnail = kwargs["jpeg_thumbnail"]
        
        return await serialize_async(message)
    
    @staticmethod
    async def build_audio(
        url: str,
        mimetype: str,
        ptt: bool = False,
        **kwargs
    ) -> bytes:
        """
        Constrói mensagem de áudio.
        
        :param url: URL do áudio
        :param mimetype: Tipo MIME
        :param ptt: Push-to-talk
        :param kwargs: Outros parâmetros
        :return: Bytes da mensagem serializada
        """
        if E2EMessage is None:
            raise RuntimeError("E2EMessage não disponível")
        
        message = E2EMessage()
        audio = message.audio_message if not ptt else message.ptv_message
        
        audio.url = url
        audio.mimetype = mimetype
        
        if "file_sha256" in kwargs:
            audio.file_sha256 = kwargs["file_sha256"]
        if "file_length" in kwargs:
            audio.file_length = kwargs["file_length"]
        if "duration" in kwargs:
            audio.seconds = kwargs["duration"]
        if "media_key" in kwargs:
            audio.media_key = kwargs["media_key"]
        
        return await serialize_async(message)
    
    @staticmethod
    async def build_document(
        url: str,
        mimetype: str,
        filename: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Constrói mensagem de documento.
        
        :param url: URL do documento
        :param mimetype: Tipo MIME
        :param filename: Nome do arquivo
        :param kwargs: Outros parâmetros
        :return: Bytes da mensagem serializada
        """
        if E2EMessage is None:
            raise RuntimeError("E2EMessage não disponível")
        
        message = E2EMessage()
        document = message.document_message
        
        document.url = url
        document.mimetype = mimetype
        
        if filename:
            document.file_name = filename
        if "title" in kwargs:
            document.title = kwargs["title"]
        if "file_sha256" in kwargs:
            document.file_sha256 = kwargs["file_sha256"]
        if "file_length" in kwargs:
            document.file_length = kwargs["file_length"]
        if "page_count" in kwargs:
            document.page_count = kwargs["page_count"]
        if "media_key" in kwargs:
            document.media_key = kwargs["media_key"]
        
        return await serialize_async(message)


class AsyncMessageParser:
    """
    Parser assíncrono para mensagens protobuf.
    Estilo whatsmeow: parsing centralizado e assíncrono.
    """
    
    @staticmethod
    async def parse(data: bytes) -> Dict[str, Any]:
        """
        Parse mensagem protobuf de forma assíncrona.
        
        :param data: Dados da mensagem
        :return: Dicionário com dados da mensagem
        """
        return AttributesConverter().proto_to_message(data)