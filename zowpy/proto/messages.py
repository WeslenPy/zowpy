"""
Protobuf Messages - Builder e Parser assíncronos para mensagens.

Estilo whatsmeow: builders e parsers centralizados e assíncronos.
"""

import asyncio
from typing import Optional, Dict, Any, List
from enum import IntEnum
from dataclasses import dataclass
from loguru import logger

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
        if E2EMessage is None:
            raise RuntimeError("E2EMessage não disponível")
        
        try:
            message = await deserialize_async(data, E2EMessage)
        except Exception as e:
            logger.error(f"Erro ao deserializar protobuf: {e}, data_len={len(data)}")
            result = {
                "type": MessageType.OTHER,
                "text": "",
                "data": {"raw": data, "error": str(e)},
            }
            return result
        
        result = {
            "type": None,
            "data": None,
        }
        
        # Log campos disponíveis para debug
        available_fields = []
        for field_descriptor in message.DESCRIPTOR.fields:
            if message.HasField(field_descriptor.name):
                available_fields.append(field_descriptor.name)
        
        if available_fields:
            logger.debug(f"Campos disponíveis no protobuf: {available_fields}")
        
        # Detecta tipo de mensagem
        if message.HasField("conversation"):
            result["type"] = MessageType.TEXT
            result["text"] = message.conversation
            result["data"] = TextMessage(text=message.conversation)
        elif message.HasField("extended_text_message"):
            ext_text = message.extended_text_message
            result["type"] = MessageType.TEXT
            result["text"] = ext_text.text if ext_text.HasField("text") else ""
            result["data"] = TextMessage(
                text=ext_text.text if ext_text.HasField("text") else "",
                context_info=ext_text.context_info.SerializeToString() if ext_text.HasField("context_info") else None
            )
        elif message.HasField("image_message"):
            img = message.image_message
            result["type"] = MessageType.IMAGE
            result["data"] = ImageMessage(
                url=img.url,
                mimetype=img.mimetype,
                caption=img.caption if img.HasField("caption") else None,
                file_sha256=img.file_sha256 if img.HasField("file_sha256") else None,
                file_length=img.file_length if img.HasField("file_length") else None,
                height=img.height if img.HasField("height") else None,
                width=img.width if img.HasField("width") else None,
                media_key=img.media_key if img.HasField("media_key") else None,
                jpeg_thumbnail=img.jpeg_thumbnail if img.HasField("jpeg_thumbnail") else None,
            )
        elif message.HasField("video_message"):
            vid = message.video_message
            result["type"] = MessageType.VIDEO
            result["data"] = VideoMessage(
                url=vid.url,
                mimetype=vid.mimetype,
                caption=vid.caption if vid.HasField("caption") else None,
                file_sha256=vid.file_sha256 if vid.HasField("file_sha256") else None,
                file_length=vid.file_length if vid.HasField("file_length") else None,
                duration=vid.seconds if vid.HasField("seconds") else None,
                height=vid.height if vid.HasField("height") else None,
                width=vid.width if vid.HasField("width") else None,
                media_key=vid.media_key if vid.HasField("media_key") else None,
                jpeg_thumbnail=vid.jpeg_thumbnail if vid.HasField("jpeg_thumbnail") else None,
            )
        elif message.HasField("audio_message"):
            aud = message.audio_message
            result["type"] = MessageType.AUDIO
            result["data"] = AudioMessage(
                url=aud.url,
                mimetype=aud.mimetype,
                file_sha256=aud.file_sha256 if aud.HasField("file_sha256") else None,
                file_length=aud.file_length if aud.HasField("file_length") else None,
                duration=aud.seconds if aud.HasField("seconds") else None,
                ptt=False,
                media_key=aud.media_key if aud.HasField("media_key") else None,
            )
        elif message.HasField("document_message"):
            doc = message.document_message
            result["type"] = MessageType.DOCUMENT
            result["data"] = DocumentMessage(
                url=doc.url,
                mimetype=doc.mimetype,
                title=doc.title if doc.HasField("title") else None,
                file_sha256=doc.file_sha256 if doc.HasField("file_sha256") else None,
                file_length=doc.file_length if doc.HasField("file_length") else None,
                page_count=doc.page_count if doc.HasField("page_count") else None,
                media_key=doc.media_key if doc.HasField("media_key") else None,
                filename=doc.file_name if doc.HasField("file_name") else None,
            )
        elif message.HasField("ptv_message"):
            # Push-to-talk video (áudio PTT)
            ptt = message.ptv_message
            result["type"] = MessageType.AUDIO
            result["data"] = AudioMessage(
                url=ptt.url,
                mimetype=ptt.mimetype,
                file_sha256=ptt.file_sha256 if ptt.HasField("file_sha256") else None,
                file_length=ptt.file_length if ptt.HasField("file_length") else None,
                duration=ptt.seconds if ptt.HasField("seconds") else None,
                ptt=True,
                media_key=ptt.media_key if ptt.HasField("media_key") else None,
            )
        elif message.HasField("sticker_message"):
            sticker = message.sticker_message
            result["type"] = MessageType.STICKER
            result["data"] = ImageMessage(
                url=sticker.url,
                mimetype=sticker.mimetype,
                file_sha256=sticker.file_sha256 if sticker.HasField("file_sha256") else None,
                file_length=sticker.file_length if sticker.HasField("file_length") else None,
                height=sticker.height if sticker.HasField("height") else None,
                width=sticker.width if sticker.HasField("width") else None,
                media_key=sticker.media_key if sticker.HasField("media_key") else None,
                jpeg_thumbnail=sticker.jpeg_thumbnail if sticker.HasField("jpeg_thumbnail") else None,
            )
        elif message.HasField("location_message"):
            loc = message.location_message
            result["type"] = MessageType.LOCATION
            result["data"] = {
                "latitude": loc.degrees_latitude if loc.HasField("degrees_latitude") else None,
                "longitude": loc.degrees_longitude if loc.HasField("degrees_longitude") else None,
                "name": loc.name if loc.HasField("name") else None,
                "address": loc.address if loc.HasField("address") else None,
            }
        elif message.HasField("contact_message"):
            contact = message.contact_message
            result["type"] = MessageType.CONTACT
            result["data"] = {
                "display_name": contact.display_name if contact.HasField("display_name") else None,
                "vcard": contact.vcard if contact.HasField("vcard") else None,
            }
        elif message.HasField("buttons_message"):
            buttons = message.buttons_message
            result["type"] = MessageType.BUTTONS
            result["text"] = buttons.content_text if buttons.HasField("content_text") else ""
            result["data"] = {
                "content_text": buttons.content_text if buttons.HasField("content_text") else None,
                "footer_text": buttons.footer_text if buttons.HasField("footer_text") else None,
                "header_type": buttons.header_type if buttons.HasField("header_type") else None,
            }
        elif message.HasField("list_message"):
            list_msg = message.list_message
            result["type"] = MessageType.LIST
            result["text"] = list_msg.description if list_msg.HasField("description") else ""
            result["data"] = {
                "title": list_msg.title if list_msg.HasField("title") else None,
                "description": list_msg.description if list_msg.HasField("description") else None,
            }
        elif message.HasField("poll_message"):
            poll = message.poll_message
            result["type"] = MessageType.POLL
            result["data"] = {
                "name": poll.name if poll.HasField("name") else None,
            }
        elif message.HasField("reaction_message"):
            reaction = message.reaction_message
            result["type"] = MessageType.REACTION
            result["data"] = {
                "key": {
                    "remote_jid": reaction.key.remote_jid if reaction.key.HasField("remote_jid") else None,
                    "from_me": reaction.key.from_me if reaction.key.HasField("from_me") else None,
                    "id": reaction.key.id if reaction.key.HasField("id") else None,
                },
                "text": reaction.text if reaction.HasField("text") else None,
            }
        else:
            result["type"] = MessageType.OTHER
            result["data"] = {"raw": data}
            # Tenta extrair texto mesmo para OTHER (pode ser um tipo desconhecido mas com conversation)
            if message.HasField("conversation"):
                result["text"] = message.conversation
        
        return result

