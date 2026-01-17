"""
Message Protocol Entities - Entidades de mensagem.

Baseado em MessageProtocolEntity do zowsuplib.
"""

import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .base import ProtocolEntity
from .enc import EncProtocolEntity


class MessageProtocolEntity(ProtocolEntity):
    """
    Entidade de mensagem <message>.
    
    Baseado em MessageProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        to: str,
        message_type: str = "text",
        message_id: Optional[str] = None,
        from_jid: Optional[str] = None,
        timestamp: Optional[int] = None,
        children: Optional[List[ProtocolEntity]] = None
    ):
        """
        Cria entidade de mensagem.
        
        Args:
            to: JID do destinatário
            message_type: Tipo da mensagem (text, image, audio, etc.)
            message_id: ID da mensagem (gerado se None)
            from_jid: JID do remetente (opcional)
            timestamp: Timestamp (gerado se None)
            children: Filhos do node (enc, proto, etc.)
        """
        if not message_id:
            message_id = self._generate_id()
        
        if timestamp is None:
            timestamp = int(time.time())
        
        attributes = {
            "to": to,
            "type": message_type,
            "id": message_id,
            "t": str(timestamp)
        }
        
        if from_jid:
            attributes["from"] = from_jid
        
        super().__init__(
            tag="message",
            attributes=attributes,
            children=children or []
        )
        
        self.message_id = message_id
        self.to = to
        self.message_type = message_type


class TextMessageProtocolEntity(MessageProtocolEntity):
    """
    Entidade de mensagem de texto.
    
    Simplifica criação de mensagens de texto com criptografia.
    """
    
    def __init__(
        self,
        to: str,
        text: str,
        enc_node: Optional[EncProtocolEntity] = None,
        proto_data: Optional[bytes] = None,
        message_id: Optional[str] = None,
        from_jid: Optional[str] = None
    ):
        """
        Cria mensagem de texto.
        
        Args:
            to: JID do destinatário
            text: Texto da mensagem
            enc_node: Node <enc> com dados criptografados
            proto_data: Dados protobuf (opcional, para node <proto>)
            message_id: ID da mensagem (gerado se None)
            from_jid: JID do remetente (opcional)
        """
        children = []
        
        if enc_node:
            children.append(enc_node)
        
        if proto_data:
            proto_node = ProtocolEntity(
                tag="proto",
                data=proto_data
            )
            children.append(proto_node)
        
        super().__init__(
            to=to,
            message_type="text",
            message_id=message_id,
            from_jid=from_jid,
            children=children
        )
        
        self.text = text


@dataclass
class MessageMetaAttributes:
    """
    Atributos de metadados para mensagens.
    
    Representa atributos adicionais que podem ser adicionados ao node <message>,
    como editado, encaminhado, etc.
    """
    
    # Atributos de edição
    edit: Optional[str] = None  # ID da mensagem original se editada
    
    # Atributos de encaminhamento
    forwarded: Optional[str] = None  # "true" se encaminhada
    
    # Atributos de participante (para grupos)
    participant: Optional[str] = None  # JID do participante que enviou
    
    # Atributos de contexto
    notify: Optional[str] = None  # Nome para notificação
    offline: Optional[str] = None  # Timestamp offline
    
    # Atributos de mídia
    media_type: Optional[str] = None  # Tipo de mídia
    media_duration: Optional[str] = None  # Duração em segundos
    
    # Atributos de status
    status: Optional[str] = None  # Status da mensagem
    
    def to_dict(self) -> Dict[str, str]:
        """
        Converte para dicionário de atributos.
        
        Returns:
            Dicionário com atributos não-None
        """
        attrs = {}
        if self.edit is not None:
            attrs["edit"] = self.edit
        if self.forwarded is not None:
            attrs["forwarded"] = self.forwarded
        if self.participant is not None:
            attrs["participant"] = self.participant
        if self.notify is not None:
            attrs["notify"] = self.notify
        if self.offline is not None:
            attrs["offline"] = self.offline
        if self.media_type is not None:
            attrs["media_type"] = self.media_type
        if self.media_duration is not None:
            attrs["media_duration"] = self.media_duration
        if self.status is not None:
            attrs["status"] = self.status
        return attrs


class ExtendedTextMessageProtocolEntity(MessageProtocolEntity):
    """
    Entidade de mensagem de texto estendida.
    
    Suporta formatação, cores, fontes, previews de links, etc.
    Baseado em ExtendedTextMessage do protobuf e ExtendedTextMessageProtocolEntity do zowsuplib.
    """
    
    # Font types (do protobuf ExtendedTextMessage.FontType)
    FONT_SANS_SERIF = 0
    FONT_SERIF = 1
    FONT_NORICAN_REGULAR = 2
    FONT_BRYNDAN_WRITE = 3
    FONT_BEBASNEUE_REGULAR = 4
    FONT_OSWALD_HEAVY = 5
    
    # Preview types (do protobuf ExtendedTextMessage.PreviewType)
    PREVIEW_NONE = 0
    PREVIEW_VIDEO = 1
    
    def __init__(
        self,
        to: str,
        text: str,
        enc_node: Optional[EncProtocolEntity] = None,
        proto_data: Optional[bytes] = None,
        message_id: Optional[str] = None,
        from_jid: Optional[str] = None,
        # Extended text fields
        matched_text: Optional[str] = None,
        canonical_url: Optional[str] = None,
        description: Optional[str] = None,
        title: Optional[str] = None,
        text_argb: Optional[int] = None,  # Cor do texto (ARGB)
        background_argb: Optional[int] = None,  # Cor de fundo (ARGB)
        font: Optional[int] = None,  # Tipo de fonte
        preview_type: Optional[int] = None,  # Tipo de preview
        jpeg_thumbnail: Optional[bytes] = None,  # Thumbnail JPEG
        view_once: Optional[bool] = None,  # View once
        meta_attributes: Optional[MessageMetaAttributes] = None
    ):
        """
        Cria mensagem de texto estendida.
        
        Args:
            to: JID do destinatário
            text: Texto da mensagem
            enc_node: Node <enc> com dados criptografados
            proto_data: Dados protobuf (opcional, para node <proto>)
            message_id: ID da mensagem (gerado se None)
            from_jid: JID do remetente (opcional)
            matched_text: Texto correspondente (para links)
            canonical_url: URL canônica (para previews)
            description: Descrição (para previews)
            title: Título (para previews)
            text_argb: Cor do texto em ARGB (0xAARRGGBB)
            background_argb: Cor de fundo em ARGB (0xAARRGGBB)
            font: Tipo de fonte (FONT_*)
            preview_type: Tipo de preview (PREVIEW_*)
            jpeg_thumbnail: Thumbnail JPEG (bytes)
            view_once: Se é view once
            meta_attributes: Atributos de metadados adicionais
        """
        children = []
        
        if enc_node:
            children.append(enc_node)
        
        if proto_data:
            proto_node = ProtocolEntity(
                tag="proto",
                data=proto_data
            )
            children.append(proto_node)
        
        # Adiciona atributos de meta se fornecidos
        attributes_extra = {}
        if meta_attributes:
            attributes_extra.update(meta_attributes.to_dict())
        
        # Chama construtor base
        super().__init__(
            to=to,
            message_type="text",
            message_id=message_id,
            from_jid=from_jid,
            children=children
        )
        
        # Adiciona atributos extras ao node
        self.attributes.update(attributes_extra)
        
        # Armazena campos estendidos
        self.text = text
        self.matched_text = matched_text
        self.canonical_url = canonical_url
        self.description = description
        self.title = title
        self.text_argb = text_argb
        self.background_argb = background_argb
        self.font = font
        self.preview_type = preview_type
        self.jpeg_thumbnail = jpeg_thumbnail
        self.view_once = view_once
        self.meta_attributes = meta_attributes
    
    def to_protobuf(self):
        """
        Converte para protobuf ExtendedTextMessage.
        
        Returns:
            e2e_pb2.Message.ExtendedTextMessage
        """
        try:
            from ...proto.e2e_pb2 import Message
            
            ext_text = Message.ExtendedTextMessage()
            ext_text.text = self.text
            
            if self.matched_text:
                ext_text.matched_text = self.matched_text
            if self.canonical_url:
                ext_text.canonical_url = self.canonical_url
            if self.description:
                ext_text.description = self.description
            if self.title:
                ext_text.title = self.title
            if self.text_argb is not None:
                ext_text.text_argb = self.text_argb
            if self.background_argb is not None:
                ext_text.background_argb = self.background_argb
            if self.font is not None:
                ext_text.font = self.font
            if self.preview_type is not None:
                ext_text.preview_type = self.preview_type
            if self.jpeg_thumbnail:
                ext_text.jpeg_thumbnail = self.jpeg_thumbnail
            if self.view_once is not None:
                ext_text.view_once = self.view_once
            
            return ext_text
        except ImportError:
            raise RuntimeError("e2e_pb2 não disponível - instale protobuf")

