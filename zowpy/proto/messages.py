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
from zowpy.protocol.entities.attributes.attributes_message import MessageAttributes

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


def _message_attributes_to_dict(attrs: MessageAttributes) -> Dict[str, Any]:
    """
    Converte MessageAttributes em dict com chaves type, text, data.
    Contrato explícito para o MessageProcessor (Fase 1 do plano).
    """
    text = ""
    msg_type = "unknown"
    data: Optional[Any] = None

    if attrs.conversation is not None:
        text = attrs.conversation
        msg_type = "text"
        data = None
    elif attrs.extended_text is not None:
        text = attrs.extended_text.text or ""
        msg_type = "text"
        data = attrs.extended_text
    elif attrs.image is not None:
        msg_type = "image"
        text = attrs.image.caption or ""
        data = attrs.image
    elif attrs.video is not None:
        msg_type = "video"
        text = attrs.video.caption or ""
        data = attrs.video
    elif attrs.audio is not None:
        msg_type = "audio"
        data = attrs.audio
    elif attrs.document is not None:
        msg_type = "document"
        text = attrs.document.title or ""
        data = attrs.document
    elif attrs.sticker is not None:
        msg_type = "sticker"
        data = attrs.sticker
    elif attrs.contact is not None:
        msg_type = "contact"
        data = attrs.contact
    elif attrs.location is not None:
        msg_type = "location"
        data = attrs.location
    elif attrs.reaction is not None:
        msg_type = "reaction"
        data = attrs.reaction
    elif attrs.buttons_response is not None:
        msg_type = "buttons_response"
        data = attrs.buttons_response
    elif attrs.list_response is not None:
        msg_type = "list_response"
        data = attrs.list_response
    elif attrs.poll_creation is not None:
        msg_type = "poll"
        data = attrs.poll_creation
    elif attrs.poll_update is not None:
        msg_type = "poll_response"
        data = attrs.poll_update
    elif attrs.product is not None:
        msg_type = "product"
        data = attrs.product
    elif attrs.template is not None:
        msg_type = "template"
        data = attrs.template
    elif attrs.protocol is not None:
        msg_type = "protocol"
        data = attrs.protocol
    elif attrs.sender_key_distribution_message is not None:
        msg_type = "sender_key_distribution"
        data = attrs.sender_key_distribution_message

    return {
        "type": msg_type,
        "text": text,
        "data": data,
    }


class AsyncMessageParser:
    """
    Parser assíncrono para mensagens protobuf.
    Estilo whatsmeow: parsing centralizado e assíncrono.
    """


    @staticmethod
    async def bytes_to_proto(data: bytes) :
        """
        Converte bytes para proto.
        """
        converter = AttributesConverter()
        return converter.protobytes_to_proto(data)
    
    @staticmethod
    async def parse(data: bytes) -> Dict[str, Any]:
        """
        Parse mensagem protobuf de forma assíncrona.

        Usa protobytes_to_message (bytes -> Message) e converte MessageAttributes
        em dict com type, text, data para o MessageProcessor.
        """
        converter = AttributesConverter()

        if isinstance(data, bytes):
            data= converter.protobytes_to_proto(data)

        attrs = converter.proto_to_message(data)

        logger.debug(f"attrs: {attrs}")
        if attrs is None:
            return {}
        if isinstance(attrs, MessageAttributes):
            return _message_attributes_to_dict(attrs)
        return {}