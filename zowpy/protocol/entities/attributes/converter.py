"""
AttributesConverter - Converte Attributes para protobuf e vice-versa.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/converter.py
"""

from typing import Optional
from loguru import logger

from ....proto.e2e_pb2 import Message
from .attributes_downloadablemedia import DownloadableMediaMessageAttributes
from .attributes_image import ImageAttributes
from .attributes_video import VideoAttributes
from .attributes_audio import AudioAttributes
from .attributes_document import DocumentAttributes
from .attributes_sticker import StickerAttributes
from .attributes_message import MessageAttributes
from .attributes_media import MediaAttributes, ContextInfoAttributes


class AttributesConverter:
    """
    Converte Attributes para protobuf e vice-versa.
    
    Singleton pattern para manter uma única instância.
    """
    
    __instance = None
    
    @classmethod
    def get(cls):
        """Retorna instância singleton do converter."""
        if cls.__instance is None:
            cls.__instance = AttributesConverter()
        return cls.__instance
    
    def downloadablemedia_to_proto(
        self,
        downloadablemedia_attributes: DownloadableMediaMessageAttributes,
        proto: object
    ) -> object:
        """
        Converte DownloadableMediaMessageAttributes para protobuf.
        
        Args:
            downloadablemedia_attributes: Atributos de mídia downloadable
            proto: Mensagem protobuf (ImageMessage, VideoMessage, etc.)
        
        Returns:
            Mensagem protobuf atualizada
        """
        logger.debug(f"downloadablemedia_to_proto: {downloadablemedia_attributes}")
        
        proto.mimetype = downloadablemedia_attributes.mimetype or ""
        proto.file_length = downloadablemedia_attributes.file_length
        proto.file_sha256 = downloadablemedia_attributes.file_sha256
        
        if downloadablemedia_attributes.url is not None:
            proto.url = downloadablemedia_attributes.url
        if downloadablemedia_attributes.media_key is not None:
            proto.media_key = downloadablemedia_attributes.media_key
        if downloadablemedia_attributes.media_key_timestamp is not None:
            proto.media_key_timestamp = downloadablemedia_attributes.media_key_timestamp
        if downloadablemedia_attributes.file_enc_sha256 is not None:
            proto.file_enc_sha256 = downloadablemedia_attributes.file_enc_sha256
        if downloadablemedia_attributes.direct_path is not None:
            proto.direct_path = downloadablemedia_attributes.direct_path
        
        return self.media_to_proto(downloadablemedia_attributes, proto)
    
    def proto_to_downloadablemedia(self, proto) -> DownloadableMediaMessageAttributes:
        """
        Converte protobuf para DownloadableMediaMessageAttributes.
        
        Args:
            proto: Mensagem protobuf (ImageMessage, VideoMessage, etc.)
        
        Returns:
            DownloadableMediaMessageAttributes
        """
        return DownloadableMediaMessageAttributes(
            mimetype=proto.mimetype if proto.HasField("mimetype") else None,
            file_length=proto.file_length,
            file_sha256=proto.file_sha256,
            url=proto.url if proto.HasField("url") else None,
            media_key=proto.media_key if proto.HasField("media_key") else None,
            media_key_timestamp=proto.media_key_timestamp if proto.HasField("media_key_timestamp") else None,
            file_enc_sha256=proto.file_enc_sha256 if proto.HasField("file_enc_sha256") else None,
            direct_path=proto.direct_path if proto.HasField("direct_path") else None,
            context_info=self.proto_to_contextinfo(proto.context_info) if proto.HasField("context_info") else None
        )
    
    def media_to_proto(self, media_attributes: MediaAttributes, proto: object) -> object:
        """
        Converte MediaAttributes para protobuf.
        
        Args:
            media_attributes: Atributos de mídia
            proto: Mensagem protobuf
        
        Returns:
            Mensagem protobuf atualizada
        """
        if media_attributes.context_info:
            # TODO: Implementar contextinfo_to_proto se necessário
            # proto.context_info.MergeFrom(self.contextinfo_to_proto(media_attributes.context_info))
            pass
        return proto
    
    def proto_to_media(self, proto) -> MediaAttributes:
        """
        Converte protobuf para MediaAttributes.
        
        Args:
            proto: Mensagem protobuf
        
        Returns:
            MediaAttributes
        """
        return MediaAttributes(
            context_info=self.proto_to_contextinfo(proto.context_info) if proto.HasField("context_info") else None
        )
    
    def proto_to_contextinfo(self, proto) -> Optional[ContextInfoAttributes]:
        """
        Converte protobuf ContextInfo para ContextInfoAttributes.
        
        Args:
            proto: ContextInfo protobuf
        
        Returns:
            ContextInfoAttributes ou None
        """
        if not proto or not proto.HasField("stanza_id"):
            return None
        
        return ContextInfoAttributes(
            stanza_id=proto.stanza_id if proto.HasField("stanza_id") else None,
            participant=proto.participant if proto.HasField("participant") else None,
            remote_jid=proto.remote_jid if proto.HasField("remote_jid") else None,
            mentioned_jid=list(proto.mentioned_jid) if proto.mentioned_jid else [],
            # Outros campos podem ser adicionados conforme necessário
        )
    
    def image_to_proto(self, image_attributes: ImageAttributes) -> Message.ImageMessage:
        """
        Converte ImageAttributes para Message.ImageMessage.
        
        Args:
            image_attributes: Atributos de imagem
        
        Returns:
            Message.ImageMessage
        """
        image_message = Message.ImageMessage()
        image_message.width = image_attributes.width
        image_message.height = image_attributes.height
        
        if image_attributes.caption is not None:
            image_message.caption = image_attributes.caption
        if image_attributes.jpeg_thumbnail is not None:
            image_message.jpeg_thumbnail = image_attributes.jpeg_thumbnail
        
        logger.debug(f"image_to_proto: {image_message}")
        logger.debug(f"image_to_proto: {image_attributes}")
        
        return self.downloadablemedia_to_proto(image_attributes.downloadablemedia_attributes, image_message)
    
    def proto_to_image(self, proto: Message.ImageMessage) -> ImageAttributes:
        """
        Converte Message.ImageMessage para ImageAttributes.
        
        Args:
            proto: Message.ImageMessage
        
        Returns:
            ImageAttributes
        """
        return ImageAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.width,
            proto.height,
            proto.caption if proto.HasField("caption") else None,
            proto.jpeg_thumbnail if proto.HasField("jpeg_thumbnail") else None
        )
    
    def video_to_proto(self, video_attributes: VideoAttributes) -> Message.VideoMessage:
        """
        Converte VideoAttributes para Message.VideoMessage.
        
        Args:
            video_attributes: Atributos de vídeo
        
        Returns:
            Message.VideoMessage
        """
        video_message = Message.VideoMessage()
        
        if video_attributes.width is not None:
            video_message.width = video_attributes.width
        if video_attributes.height is not None:
            video_message.height = video_attributes.height
        if video_attributes.seconds is not None:
            video_message.seconds = video_attributes.seconds
        if video_attributes.gif_playback is not None:
            video_message.gif_playback = video_attributes.gif_playback
        if video_attributes.jpeg_thumbnail is not None:
            video_message.jpeg_thumbnail = video_attributes.jpeg_thumbnail
        if video_attributes.gif_attribution is not None:
            video_message.gif_attribution = video_attributes.gif_attribution
        if video_attributes.caption is not None:
            video_message.caption = video_attributes.caption
        if video_attributes.streaming_sidecar is not None:
            video_message.streaming_sidecar = video_attributes.streaming_sidecar
        
        return self.downloadablemedia_to_proto(video_attributes.downloadablemedia_attributes, video_message)
    
    def proto_to_video(self, proto: Message.VideoMessage) -> VideoAttributes:
        """
        Converte Message.VideoMessage para VideoAttributes.
        
        Args:
            proto: Message.VideoMessage
        
        Returns:
            VideoAttributes
        """
        return VideoAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.width,
            proto.height,
            proto.seconds,
            proto.caption if proto.HasField("caption") else None,
            proto.gif_playback if proto.HasField("gif_playback") else None,
            proto.jpeg_thumbnail if proto.HasField("jpeg_thumbnail") else None,
            proto.gif_attribution if proto.HasField("gif_attribution") else None,
            proto.streaming_sidecar if proto.HasField("streaming_sidecar") else None
        )
    
    def audio_to_proto(self, audio_attributes: AudioAttributes) -> Message.AudioMessage:
        """
        Converte AudioAttributes para Message.AudioMessage.
        
        Args:
            audio_attributes: Atributos de áudio
        
        Returns:
            Message.AudioMessage
        """
        audio_message = Message.AudioMessage()
        
        if audio_attributes.seconds is not None:
            audio_message.seconds = audio_attributes.seconds
        if audio_attributes.ptt is not None:
            audio_message.ptt = audio_attributes.ptt
        if audio_attributes.waveform is not None:
            audio_message.waveform = audio_attributes.waveform
        if audio_attributes.streaming_sidecar is not None:
            audio_message.streaming_sidecar = audio_attributes.streaming_sidecar
        
        return self.downloadablemedia_to_proto(audio_attributes.downloadablemedia_attributes, audio_message)
    
    def proto_to_audio(self, proto: Message.AudioMessage) -> AudioAttributes:
        """
        Converte Message.AudioMessage para AudioAttributes.
        
        Args:
            proto: Message.AudioMessage
        
        Returns:
            AudioAttributes
        """
        waveform = None
        if proto.HasField("waveform"):
            waveform = proto.waveform
        
        streaming_sidecar = None
        if proto.HasField("streaming_sidecar"):
            streaming_sidecar = proto.streaming_sidecar
        
        return AudioAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.seconds,
            proto.ptt,
            streaming_sidecar,
            waveform
        )
    
    def document_to_proto(self, document_attributes: DocumentAttributes) -> Message.DocumentMessage:
        """
        Converte DocumentAttributes para Message.DocumentMessage.
        
        Args:
            document_attributes: Atributos de documento
        
        Returns:
            Message.DocumentMessage
        """
        doc_message = Message.DocumentMessage()
        
        if document_attributes.file_name is not None:
            doc_message.file_name = document_attributes.file_name
        if document_attributes.file_length is not None:
            doc_message.file_length = document_attributes.file_length
        if document_attributes.title is not None:
            doc_message.title = document_attributes.title
        if document_attributes.page_count is not None:
            doc_message.page_count = document_attributes.page_count
        if document_attributes.jpeg_thumbnail is not None:
            doc_message.jpeg_thumbnail = document_attributes.jpeg_thumbnail
        if document_attributes.caption is not None:
            doc_message.caption = document_attributes.caption
        
        return self.downloadablemedia_to_proto(document_attributes.downloadablemedia_attributes, doc_message)
    
    def proto_to_document(self, proto: Message.DocumentMessage) -> DocumentAttributes:
        """
        Converte Message.DocumentMessage para DocumentAttributes.
        
        Args:
            proto: Message.DocumentMessage
        
        Returns:
            DocumentAttributes
        """
        return DocumentAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.file_name if proto.HasField("file_name") else None,
            proto.file_length if proto.HasField("file_length") else None,
            proto.title if proto.HasField("title") else None,
            proto.page_count if proto.HasField("page_count") else None,
            proto.jpeg_thumbnail if proto.HasField("jpeg_thumbnail") else None,
            proto.caption if proto.HasField("caption") else None
        )
    
    def sticker_to_proto(self, sticker_attributes: StickerAttributes) -> Message.StickerMessage:
        """
        Converte StickerAttributes para Message.StickerMessage.
        
        Args:
            sticker_attributes: Atributos de sticker
        
        Returns:
            Message.StickerMessage
        """
        sticker_message = Message.StickerMessage()
        
        if sticker_attributes.width is not None:
            sticker_message.width = sticker_attributes.width
        if sticker_attributes.height is not None:
            sticker_message.height = sticker_attributes.height
        if sticker_attributes.png_thumbnail is not None:
            sticker_message.png_thumbnail = sticker_attributes.png_thumbnail
        if sticker_attributes.is_animated is not None:
            sticker_message.is_animated = sticker_attributes.is_animated
        if sticker_attributes.is_avatar is not None:
            sticker_message.is_avatar = sticker_attributes.is_avatar
        if sticker_attributes.is_ai_sticker is not None:
            sticker_message.is_ai_sticker = sticker_attributes.is_ai_sticker
        if sticker_attributes.is_lottie is not None:
            sticker_message.is_lottie = sticker_attributes.is_lottie
        if sticker_attributes.sticker_sent_ts is not None:
            sticker_message.sticker_sent_ts = int(sticker_attributes.sticker_sent_ts)
        
        return self.downloadablemedia_to_proto(sticker_attributes.downloadablemedia_attributes, sticker_message)
    
    def proto_to_sticker(self, proto: Message.StickerMessage) -> StickerAttributes:
        """
        Converte Message.StickerMessage para StickerAttributes.
        
        Args:
            proto: Message.StickerMessage
        
        Returns:
            StickerAttributes
        """
        return StickerAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.width,
            proto.height,
            proto.png_thumbnail if proto.HasField("png_thumbnail") else None,
            proto.is_animated if proto.HasField("is_animated") else False,
            proto.sticker_sent_ts if proto.HasField("sticker_sent_ts") else None,
            proto.is_avatar if proto.HasField("is_avatar") else False,
            proto.is_ai_sticker if proto.HasField("is_ai_sticker") else False,
            proto.is_lottie if proto.HasField("is_lottie") else False
        )
    
    def message_to_protobytes(self, message_attributes: MessageAttributes) -> bytes:
        """
        Converte MessageAttributes para bytes protobuf.
        
        Args:
            message_attributes: Atributos da mensagem
        
        Returns:
            bytes: Dados protobuf serializados
        """
        message = Message()
        
        if message_attributes.image is not None:
            message.image_message.CopyFrom(self.image_to_proto(message_attributes.image))
        elif message_attributes.video is not None:
            message.video_message.CopyFrom(self.video_to_proto(message_attributes.video))
        elif message_attributes.audio is not None:
            message.audio_message.CopyFrom(self.audio_to_proto(message_attributes.audio))
        elif message_attributes.document is not None:
            message.document_message.CopyFrom(self.document_to_proto(message_attributes.document))
        elif message_attributes.sticker is not None:
            message.sticker_message.CopyFrom(self.sticker_to_proto(message_attributes.sticker))
        elif message_attributes.conversation is not None:
            message.conversation = message_attributes.conversation
        
        return message.SerializeToString()
    
    def proto_to_message(self, proto: Message) -> MessageAttributes:
        """
        Converte Message protobuf para MessageAttributes.
        
        Args:
            proto: Message protobuf
        
        Returns:
            MessageAttributes
        """
        if proto.HasField("image_message"):
            return MessageAttributes(image=self.proto_to_image(proto.image_message))
        elif proto.HasField("video_message"):
            return MessageAttributes(video=self.proto_to_video(proto.video_message))
        elif proto.HasField("audio_message"):
            return MessageAttributes(audio=self.proto_to_audio(proto.audio_message))
        elif proto.HasField("document_message"):
            return MessageAttributes(document=self.proto_to_document(proto.document_message))
        elif proto.HasField("sticker_message"):
            return MessageAttributes(sticker=self.proto_to_sticker(proto.sticker_message))
        elif proto.HasField("conversation"):
            return MessageAttributes(conversation=proto.conversation)
        else:
            return MessageAttributes()

