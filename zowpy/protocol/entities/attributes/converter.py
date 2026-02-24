"""
AttributesConverter - Converte Attributes para protobuf e vice-versa.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/converter.py
"""

from typing import Optional
from loguru import logger

from zowpy.protocol.entities.attributes.attributes_buttons_response import ButtonsResponseAttributes
from zowpy.protocol.entities.attributes.attributes_contact import ContactAttributes
from zowpy.protocol.entities.attributes.attributes_disappearing_mode import DisappearingModeAttributes
from zowpy.protocol.entities.attributes.attributes_history_sync_notification import HistorySyncNotificationAttribute
from zowpy.protocol.entities.attributes.attributes_list_response import ListResponseAttributes
from zowpy.protocol.entities.attributes.attributes_message_key import MessageKeyAttributes
from zowpy.protocol.entities.attributes.attributes_poll_creation import PollCreationAttributes
from zowpy.protocol.entities.attributes.attributes_poll_updates import PollUpdateAttributes
from zowpy.protocol.entities.attributes.attributes_product import ProductAttributes
from zowpy.protocol.entities.attributes.attributes_protocol import ProtocolAttributes
from zowpy.protocol.entities.attributes.attributes_reaction import ReactionAttributes
from zowpy.protocol.entities.attributes.attributes_reply import ExternalAdReplyAttributes
from zowpy.protocol.entities.attributes.attributes_security_notification_sync import InitialSecurityNotificationSettingSyncAttribute
from zowpy.protocol.entities.attributes.attributes_sender_key_distribution_message import SenderKeyDistributionMessageAttributes
from zowpy.protocol.entities.attributes.attributes_template import TemplateAttributes

from ....proto.e2e_pb2 import (Message,ContextInfo,MessageContextInfo,HydratedTemplateButton,DisappearingMode)
from .attributes_downloadablemedia import DownloadableMediaMessageAttributes
from .attributes_image import ImageAttributes
from .attributes_video import VideoAttributes
from .attributes_audio import AudioAttributes
from .attributes_document import DocumentAttributes
from .attributes_sticker import StickerAttributes
from .attributes_message import MessageAttributes
from .attributes_extendedtext import ExtendedTextAttributes
from .attributes_media import MediaAttributes, ContextInfoAttributes
import os
import time
from zowpy.proto import protocol_pb2



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
        # type: (MediaAttributes, object) -> object
        if media_attributes.context_info:
            proto.context_info.MergeFrom(self.contextinfo_to_proto(media_attributes.context_info))

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
            quoted_message=self.proto_to_message(proto.quoted_message)
            if proto.HasField("quoted_message") else None,
            remote_jid=proto.remote_jid if proto.HasField("remote_jid") else None,
            mentioned_jid=proto.mentioned_jid if len(proto.mentioned_jid) else [],            
            #edit_version=proto.edit_version if proto.HasField("edit_version") else None,    #deprecated
            #revoke_message=proto.revoke_message if proto.HasField("revoke_message") else None #deprecated
            edit_version = None,
            revoke_message = None,
            entry_point_conversion_source = proto.entry_point_conversion_source if proto.HasField("entry_point_conversion_source") else None,
            entry_point_conversion_app = proto.entry_point_conversion_app if proto.HasField("entry_point_conversion_app") else None,
            entry_point_conversion_delay_seconds = proto.entry_point_conversion_delay_seconds if proto.HasField("entry_point_conversion_delay_seconds") else None,
            conversion_delay_seconds=proto.conversion_delay_seconds if proto.HasField("conversion_delay_seconds") else None,
            forwarding_score=proto.forwarding_score if proto.HasField("forwarding_score") else None,
            is_forwarded= proto.is_forwarded if proto.HasField("is_forwarded") else None,
            expiration=  proto.expiration if proto.HasField("expiration") else None,
            ephemeral_setting_timestamp=  proto.ephemeral_setting_timestamp if proto.HasField("ephemeral_setting_timestamp") else None,
            disappearing_mode=self.proto_to_disappearing_mode(proto.disappearing_mode) if proto.HasField("disappearing_mode") else None,    
            external_ad_reply=self.proto_to_external_ad_reply(proto.external_ad_reply) if proto.HasField("external_ad_reply") else None        
        )
        


    def app_state_sync_key_share_to_proto(self,app_state_sync_key_share_attributes):

        message = Message.AppStateSyncKeyShare()

        for key in app_state_sync_key_share_attributes.keys:
            message.keys.append(self.app_state_sync_key_to_proto(key))
        
        return message
            

    def app_state_sync_key_to_proto(self,app_state_sync_key_attributes):
        message =Message.AppStateSyncKey()
        message.key_id.MergeFrom(self.app_state_sync_key_id_to_proto(app_state_sync_key_attributes.key_id))
        message.key_data.MergeFrom(self.app_state_sync_key_data_to_proto(app_state_sync_key_attributes.key_data))

        return message

    def app_state_sync_key_id_to_proto(self,app_state_sync_key_id_attributes):
        message = Message.AppStateSyncKeyId()
        message.key_id = app_state_sync_key_id_attributes.key_id
        return message


    def app_state_sync_key_data_to_proto(self,app_state_sync_key_data_attributes):        
        message = Message.AppStateSyncKeyData()
        message.key_data = app_state_sync_key_data_attributes.key_data
        message.timestamp = app_state_sync_key_data_attributes.timestamp
        message.fingerprint.MergeFrom(self.app_state_sync_key_fingerprint_to_proto(app_state_sync_key_data_attributes.fingerprint))
        return message
    
    def app_state_sync_key_fingerprint_to_proto(self,app_state_sync_key_fingerprint_attribute):
        message = Message.AppStateSyncKeyFingerprint()
        message.raw_id = app_state_sync_key_fingerprint_attribute.raw_id
        message.current_index = app_state_sync_key_fingerprint_attribute.current_index
        for idx in app_state_sync_key_fingerprint_attribute.device_indexes:
            message.device_indexes.append(idx)
        return message


    
    def proto_to_message_key(self, proto):
        return MessageKeyAttributes(
            proto.remote_jid, proto.from_me, proto.id, proto.participant 
        )


    def proto_to_protocol(self, proto):
        return ProtocolAttributes(
            self.proto_to_message_key(proto.key),
            proto.type,
            initial_security_notification_setting_sync=self.proto_to_initial_security_notification_setting_sync(proto.initial_security_notification_setting_sync) if proto.HasField("initial_security_notification_setting_sync") else None,
            history_sync_notification=HistorySyncNotificationAttribute.decodeFrom(proto.history_sync_notification) if proto.HasField("history_sync_notification") else None,
            edited_message=self.proto_to_message(proto.edited_message) if proto.HasField("edited_message") else None,
            ephemeral_expiration=proto.ephemeral_expiration if proto.HasField("ephemeral_expiration") else None,
            disappearing_mode=self.proto_to_disappearing_mode(proto.disappearing_mode) if proto.HasField("disappearing_mode") else None,
        )
    

    def proto_to_disappearing_mode(self,proto):
        return DisappearingModeAttributes(
            initiator=proto.initiator if proto.HasField("initiator") else None,
            trigger=proto.trigger if proto.HasField("trigger") else None,
            initiatedByMe=proto.initiatedByMe if proto.HasField("initiatedByMe") else None,
            initiatorDeviceJid=proto.initiatorDeviceJid if proto.HasField("initiatorDeviceJid") else None
        )
    
    def proto_to_initial_security_notification_setting_sync(self,proto):
        return InitialSecurityNotificationSettingSyncAttribute(
            security_notification_enabled=proto.security_notification_enabled              
        )        

    def proto_to_external_ad_reply(self,proto):
        return ExternalAdReplyAttributes(
            title = proto.title if proto.HasField("title") else None,
            media_type=  proto.media_type if proto.HasField("media_type") else None,
            thumbnail = proto.thumbnail if proto.HasField("thumbnail") else None,
            source_url = proto.source_url if proto.HasField("source_url") else None,
            contains_auto_reply= proto.contains_auto_reply if proto.HasField("contains_auto_reply") else None,
            render_larger_thumbnail= proto.render_larger_thumbnail if proto.HasField("render_larger_thumbnail") else None,
            show_ad_attribution=  proto.show_ad_attribution if proto.HasField("show_ad_attribution") else None
        )       
    
    def contextinfo_to_proto(self, contextinfo_attributes: ContextInfoAttributes) -> ContextInfo:
        """Converte ContextInfoAttributes para protobuf."""

        cxt_info = ContextInfo()
        if contextinfo_attributes.stanza_id is not None:
            cxt_info.stanza_id = contextinfo_attributes.stanza_id
        if contextinfo_attributes.participant is not None:
            cxt_info.participant = contextinfo_attributes.participant
        if contextinfo_attributes.quoted_message:
            cxt_info.quoted_message.MergeFrom(self.message_to_proto(contextinfo_attributes.quoted_message))
        if contextinfo_attributes.remote_jid is not None:
            cxt_info.remote_jid = contextinfo_attributes.remote_jid
        if contextinfo_attributes.mentioned_jid is not None and len(contextinfo_attributes.mentioned_jid):
            cxt_info.mentioned_jid[:] = contextinfo_attributes.mentioned_jid

        if contextinfo_attributes.conversion_delay_seconds is not None:
            cxt_info.conversion_delay_seconds = contextinfo_attributes.conversion_delay_seconds

        if contextinfo_attributes.forwarding_score is not None:
            cxt_info.forwarding_score = contextinfo_attributes.forwarding_score
        if contextinfo_attributes.is_forwarded is not None:
            cxt_info.is_forwarded = contextinfo_attributes.is_forwarded

        if contextinfo_attributes.expiration is not None:
            cxt_info.expiration = contextinfo_attributes.expiration       

        if contextinfo_attributes.ephemeral_setting_timestamp is not None:
            cxt_info.ephemeral_setting_timestamp = contextinfo_attributes.ephemeral_setting_timestamp   

        if contextinfo_attributes.disappearing_mode is not None:
            cxt_info.disappearing_mode.MergeFrom(self.disappearing_mode_to_proto(contextinfo_attributes.disappearing_mode))

        if contextinfo_attributes.external_ad_reply is not None:
            cxt_info.external_ad_reply.MergeFrom(self.external_ad_reply_to_proto(contextinfo_attributes.external_ad_reply))
                        
        if contextinfo_attributes.business_message_forward_info is not None:
            cxt_info.business_message_forward_info.MergeFrom(self.business_message_forward_info_to_proto(contextinfo_attributes.business_message_forward_info))

        if contextinfo_attributes.entry_point_conversion_source is not None:
            cxt_info.entry_point_conversion_source = contextinfo_attributes.entry_point_conversion_source

        if contextinfo_attributes.entry_point_conversion_app is not None:
            cxt_info.entry_point_conversion_app = contextinfo_attributes.entry_point_conversion_app

        if contextinfo_attributes.entry_point_conversion_delay_seconds is not None:
            cxt_info.entry_point_conversion_delay_seconds = contextinfo_attributes.entry_point_conversion_delay_seconds

        return cxt_info

    def external_ad_reply_to_proto(self,attributes):
        
        eara = ContextInfo.ExternalAdReplyInfo()
        if attributes.title is not None:
            eara.title =  attributes.title

        if attributes.body is not None:
            eara.body =  attributes.body

        if attributes.media_type is not None:
            eara.media_type =  attributes.media_type

        if attributes.thumbnail_url is not None:
            eara.thumbnail_url =  attributes.thumbnail_url                     

        if attributes.media_url is not None:
            eara.media_url =  attributes.media_url        

        if attributes.thumbnail is not None:
            eara.thumbnail =  attributes.thumbnail     

        if attributes.source_type is not None:
            eara.source_type =  attributes.source_type        

        if attributes.source_id is not None:
            eara.source_id =  attributes.source_id               

        if attributes.source_url is not None:
            eara.source_url =  attributes.source_url         
            
        if attributes.contains_auto_reply is not None:
            eara.contains_auto_reply =  attributes.contains_auto_reply       

        if attributes.render_larger_thumbnail is not None:
            eara.render_larger_thumbnail =  attributes.render_larger_thumbnail  

        if attributes.show_ad_attribution is not None:
            eara.show_ad_attribution =  attributes.show_ad_attribution                                           

        return eara


    def message_to_proto(self, message_attributes):
        
        # type: (MessageAttributes) -> Message
        message = Message()
        mctx = MessageContextInfo()

        if message_attributes.message_secret is not None and message_attributes.message_secret != b'':
            mctx.message_secret = message_attributes.message_secret

        # mctx.device_list_metadata.sender_timestamp = int(time.time())
        # mctx.device_list_metadata_version = 2
        #mctx.device_list_metadata.sender_account_type = 0
        #mctx.device_list_metadata.receiver_account_type = 0
        

        if message_attributes.reaction is None:
            if mctx.message_secret is not None and mctx.message_secret != b'':
                message.message_context_info.MergeFrom(mctx)

        if message_attributes.conversation:
            message.conversation = message_attributes.conversation

        if message_attributes.poll_creation:
            message.pollCreationMessageV3.MergeFrom(self.poll_creation_to_proto(message_attributes.poll_creation))
            message.message_context_info.message_secret = message_attributes.poll_creation.message_secret
    
        if message_attributes.image:
            message.image_message.MergeFrom(self.image_to_proto(message_attributes.image))
        if message_attributes.contact:
            message.contact_message.MergeFrom(self.contact_to_proto(message_attributes.contact))
        if message_attributes.location:
            message.location_message.MergeFrom(self.location_to_proto(message_attributes.location))
        if message_attributes.extended_text:
            message.extended_text_message.MergeFrom(self.extendedtext_to_proto(message_attributes.extended_text))

        if message_attributes.document:
            message.document_message.MergeFrom(self.document_to_proto(message_attributes.document))
        if message_attributes.audio:
            message.audio_message.MergeFrom(self.audio_to_proto(message_attributes.audio))
        if message_attributes.video:
            message.video_message.MergeFrom(self.video_to_proto(message_attributes.video))
        if message_attributes.sticker:
            message.sticker_message.MergeFrom(self.sticker_to_proto(message_attributes.sticker))

        if message_attributes.reaction:
            message.reaction_message.MergeFrom(self.reaction_to_proto(message_attributes.reaction))
            
        if message_attributes.template:                     
            message.view_once_message.message.template_message.MergeFrom(self.template_to_proto(message_attributes.template))   
        if message_attributes.buttons:                     
            message.view_once_message.message.buttons_message.MergeFrom(self.buttons_to_proto(message_attributes.buttons))   
        if message_attributes.list:                     
            message.view_once_message.message.list_message.MergeFrom(self.list_to_proto(message_attributes.list))   

        if message_attributes.product:
            message.product_message.MergeFrom(self.product_to_proto(message_attributes.product))
        
        if message_attributes.interactive:
            message.interactive_message.MergeFrom(self.interactive_to_proto(message_attributes.interactive))

        if message_attributes.sender_key_distribution_message:
            message.sender_key_distribution_message.MergeFrom(
                self.sender_key_distribution_message_to_proto(message_attributes.sender_key_distribution_message)
            )
            
        if message_attributes.protocol:
            message.protocol_message.MergeFrom(self.protocol_to_proto(message_attributes.protocol))
        
        
        return message

    def reaction_to_proto(self,reaction_attributes):
        m = Message.ReactionMessage()
        m.key.id = reaction_attributes.msgid
        m.key.remote_jid = reaction_attributes.remote_jid
        m.key.from_me = reaction_attributes.from_me
        # Inclui participant no key se fornecido (necessário para grupos)
        if reaction_attributes.participant is not None:
            m.key.participant = reaction_attributes.participant
        m.text = reaction_attributes.text
        m.sender_timestamp_ms = reaction_attributes.sender_timestamp_ms
        return m
    
    def proto_to_reaction(self,proto):
        return ReactionAttributes(
            msgid=proto.key.id,
            remote_jid= proto.key.remote_jid,
            from_me = proto.key.from_me,
            text = proto.text,
            sender_timestamp_ms= proto.sender_timestamp_ms,
            participant=proto.key.participant if proto.key.HasField("participant") else None
        )
    def sticker_to_proto(self, sticker_attributes):
        m =Message.StickerMessage()
        if sticker_attributes.width is not None:
            m.width = sticker_attributes.width
        if sticker_attributes.height is not None:
            m.height = sticker_attributes.height
        if sticker_attributes.png_thumbnail is not None:
            m.png_thumbnail = sticker_attributes.png_thumbnail
        if sticker_attributes.is_animated is not None:
            m.is_animated = sticker_attributes.is_animated        
        if sticker_attributes.is_avatar is not None:
            m.is_avatar = sticker_attributes.is_avatar  
        if sticker_attributes.is_ai_sticker is not None:
            m.is_ai_sticker = sticker_attributes.is_ai_sticker
        if sticker_attributes.is_lottie is not None:
            m.is_lottie = sticker_attributes.is_lottie
        if sticker_attributes.sticker_sent_ts is not None:
            m.sticker_sent_ts = int(sticker_attributes.sticker_sent_ts)        

        return self.downloadablemedia_to_proto(sticker_attributes.downloadablemedia_attributes, m)

    def proto_to_sender_key_distribution_message(self, proto):
        return SenderKeyDistributionMessageAttributes(
            proto.group_id, proto.axolotl_sender_key_distribution_message
        )


    def sender_key_distribution_message_to_proto(self, sender_key_distribution_message_attributes):
        message = Message.SenderKeyDistributionMessage()
        message.group_id = sender_key_distribution_message_attributes.group_id
        message.axolotl_sender_key_distribution_message = \
            sender_key_distribution_message_attributes.axolotl_sender_key_distribution_message
        return message


    def message_key_to_proto(self, message_key):
        out = protocol_pb2.MessageKey()
        out.remote_jid = message_key.remote_jid
        out.from_me = message_key.from_me
        if message_key.id is not None:
            out.id = message_key.id
        if message_key.participant:
            out.participant = message_key.participant.participant
        return out
    
    def protocol_to_proto(self, protocol):
        # type: (ProtocolAttributes) -> Message.ProtocolMessage
        
        message = Message.ProtocolMessage()
        message.type = protocol.type

        if protocol.key is not None:
            message.key.MergeFrom(self.message_key_to_proto(protocol.key))        
        if protocol.initial_security_notification_setting_sync is not None: 
            message.initial_security_notification_setting_sync.MergeFrom(self.initial_security_notification_setting_sync_to_proto(protocol.initial_security_notification_setting_sync))

        if protocol.app_state_sync_key_share is not None:
            message.app_state_sync_key_share.MergeFrom(self.app_state_sync_key_share_to_proto(protocol.app_state_sync_key_share))

        if protocol.history_sync_notification is not None:
            message.history_sync_notification.MergeFrom(protocol.history_sync_notification.encode())

        if protocol.edited_message is not None:
            message.edited_message.MergeFrom(self.message_to_proto(protocol.edited_message))

        if protocol.ephemeral_expiration is not None:
            message.ephemeral_expiration = protocol.ephemeral_expiration

        if protocol.disappearing_mode is not None:
            message.disappearing_mode.MergeFrom(self.disappearing_mode_to_proto(protocol.disappearing_mode))
       
        return message
    

    def initial_security_notification_setting_sync_to_proto(self,initial_security_notification_setting_sync_attributes):
        message = Message.InitialSecurityNotificationSettingSync()
        message.security_notification_enabled = initial_security_notification_setting_sync_attributes.security_notification_enabled        
        return message

    def business_message_forward_info_to_proto(self,attrs):
        bmfi = ContextInfo.BusinessMessageForwardInfo()
        if attrs.business_owner_jid is not None:
            bmfi.businessOwnerJID = attrs.business_owner_jid
        return bmfi



    def disappearing_mode_to_proto(self,disappearing_mode_attributes):
        message = DisappearingMode()        
        if disappearing_mode_attributes.initiator is not None:
            message.initiator = disappearing_mode_attributes.initiator 

        if disappearing_mode_attributes.trigger is not None:
            message.trigger = disappearing_mode_attributes.trigger

        if disappearing_mode_attributes.initiatedByMe is not None:
            message.initiatedByMe = disappearing_mode_attributes.initiatedByMe
        if disappearing_mode_attributes.initiatorDeviceJid is not None:
            message.initiatorDeviceJid = disappearing_mode_attributes.initiatorDeviceJid if disappearing_mode_attributes.initiatorDeviceJid else None
        return message

    def extendedtext_to_proto(self, extended_text_attributes: ExtendedTextAttributes) -> Message.ExtendedTextMessage:
        """Converte ExtendedTextAttributes para protobuf."""


        logger.info(f"extended_text_attributes: {extended_text_attributes}")
        logger.info(f"extended_text_attributes.context_info: {extended_text_attributes.context_info}")
        proto = Message.ExtendedTextMessage()
        proto.text = extended_text_attributes.text
        
        if extended_text_attributes.matched_text:
            proto.matched_text = extended_text_attributes.matched_text
        if extended_text_attributes.canonical_url:
            proto.canonical_url = extended_text_attributes.canonical_url
        if extended_text_attributes.description:
            proto.description = extended_text_attributes.description
        if extended_text_attributes.title:
            proto.title = extended_text_attributes.title
        if extended_text_attributes.text_argb is not None:
            proto.text_argb = extended_text_attributes.text_argb
        if extended_text_attributes.background_argb is not None:
            proto.background_argb = extended_text_attributes.background_argb
        if extended_text_attributes.font is not None:
            proto.font = extended_text_attributes.font
        if extended_text_attributes.preview_type is not None:
            proto.preview_type = extended_text_attributes.preview_type
        if extended_text_attributes.jpeg_thumbnail:
            proto.jpeg_thumbnail = extended_text_attributes.jpeg_thumbnail
        if extended_text_attributes.doNotPlayInline is not None:
            proto.do_not_play_inline = extended_text_attributes.doNotPlayInline
        if extended_text_attributes.invite_link_group_type_v2 is not None:
            proto.invite_link_group_type_v2 = extended_text_attributes.invite_link_group_type_v2
            
        if extended_text_attributes.context_info is not None:
            proto.context_info.MergeFrom(self.contextinfo_to_proto(extended_text_attributes.context_info))
            
        return proto

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
            proto.context_info.MergeFrom(self.contextinfo_to_proto(media_attributes.context_info))
        return proto


    def proto_to_sticker(self, proto):
        return StickerAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.width, proto.height, proto.png_thumbnail,proto.is_animated, proto.sticker_sent_ts,proto.is_avatar,proto.is_ai_sticker,proto.is_lottie
        )

    def proto_to_template(self, proto):      
        buttons = []

        for item in proto.hydrated_template.hydrated_buttons:
            if item.HasField("url_button"):
                buttons.append({
                    "type":"url",
                    "text":item.url_button.display_text,
                    "url":item.url_button.url                    
                })
            if item.HasField("call_button"):
                buttons.append({
                    "type":"call",
                    "text":item.call_button.display_text,
                    "phone":item.call_button.phone_number
                })

        return TemplateAttributes(
            proto.hydrated_template.hydrated_content_text,
            buttons           
        )   

    def message_to_protobytes(self, message: MessageAttributes) -> bytes:
        """
        Converte MessageAttributes para bytes protobuf.
        
        Args:
            message_attributes: Atributos da mensagem
        
        Returns:
            bytes: Dados protobuf serializados
        """
        return self.message_to_proto(message).SerializeToString()


    def interactive_header_to_proto(self,attrs):
        m = Message.InteractiveMessage.Header()
        m.title = attrs.title
        m.subtitle = attrs.subtitle

        attachment = False
        if attrs.image :
            attachment=True
            m.image_message.MergeFrom(self.image_to_proto(attrs.image))

        if attrs.document :
            attachment=True
            m.document_message.MergeFrom(self.document_to_proto(attrs.document))

        if attrs.video :
            attachment=True
            m.document_message.MergeFrom(self.video_to_proto(attrs.video))

        if attrs.thumbnail:
            attachment=True
            m.jpeg_thumbnail = attrs.thumbnail

        m.has_media_attachment = attachment

        return m


    def document_to_proto(self, document_attributes):

        m = Message.DocumentMessage()
        if document_attributes.file_name is not None:
            m.file_name = document_attributes.file_name
        if document_attributes.file_length is not None:
            m.file_length = document_attributes.file_length
        if document_attributes.title is not None:
            m.title = document_attributes.title
        if document_attributes.page_count is not None:
            m.page_count = document_attributes.page_count
        if document_attributes.jpeg_thumbnail is not None:
            m.jpeg_thumbnail = document_attributes.jpeg_thumbnail

        if document_attributes.caption is not None:
            m.caption = document_attributes.caption

        return self.downloadablemedia_to_proto(document_attributes.downloadablemedia_attributes, m)


    def proto_to_document(self, proto):        
        
        return DocumentAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.file_name if proto.HasField("file_name") else None,
            proto.file_length if proto.HasField("file_length") else None,
            proto.title if proto.HasField("title") else None,
            proto.page_count if proto.HasField("page_count") else None,
            proto.jpeg_thumbnail if proto.HasField("jpeg_thumbnail") else None,
            proto.caption if proto.HasField("caption") else None
        )

    def audio_to_proto(self, audio_attributes):
        m = Message.AudioMessage()
        if audio_attributes.seconds is not None:
            m.seconds = audio_attributes.seconds
        if audio_attributes.ptt is not None:
            m.ptt = audio_attributes.ptt
        if audio_attributes.waveform is not None:
            m.waveform = audio_attributes.waveform
        if audio_attributes.streaming_sidecar is not None:
            m.streaming_sidecar = audio_attributes.streaming_sidecar

        return self.downloadablemedia_to_proto(audio_attributes.downloadablemedia_attributes, m)


    def proto_to_audio(self, proto):
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
    
    def video_to_proto(self, video_attributes):
        m = Message.VideoMessage()
        if video_attributes.width is not None:
            m.width = video_attributes.width
        if video_attributes.height is not None:
            m.height = video_attributes.height
        if video_attributes.seconds is not None:
            m.seconds = video_attributes.seconds
        if video_attributes.gif_playback is not None:
            m.gif_playback = video_attributes.gif_playback
        if video_attributes.jpeg_thumbnail is not None:
            m.jpeg_thumbnail = video_attributes.jpeg_thumbnail
        if video_attributes.gif_attribution is not None:
            m.gif_attribution = video_attributes.gif_attribution
        if video_attributes.caption is not None:
            m.caption = video_attributes.caption
        if video_attributes.streaming_sidecar is not None:
            m.streaming_sidecar = video_attributes.streaming_sidecar

        return self.downloadablemedia_to_proto(video_attributes.downloadablemedia_attributes, m)


    def interactive_to_proto(self,interactive_attributes):
        m = Message.InteractiveMessage()
        if interactive_attributes.header:
            m.header.MergeFrom(self.interactive_header_to_proto(interactive_attributes.header))

        if interactive_attributes.body:
            m.body.text = interactive_attributes.body

        if interactive_attributes.footer:
            m.footer.text= interactive_attributes.footer

        if interactive_attributes.buttons:
            for btn_item in interactive_attributes.buttons:
                button = Message.InteractiveMessage.NativeFlowMessage.NativeFlowButton()
                button.name = btn_item["name"]
                button.params_json = btn_item["params_json"]
                m.native_flow_message.buttons.extend([button])
                                     
        m.native_flow_message.message_version=1

        return m

    
    def proto_to_message(self, proto: Message,from_jid=None,message_db=None) -> MessageAttributes:
        """
        Converte Message protobuf para MessageAttributes.
        
        Args:
            proto: Message protobuf
        
        Returns:
            MessageAttributes
        """
        if proto.HasField("device_sent_message"):            
            proto = proto.device_sent_message.message            

        if proto.HasField("view_once_message"):
            proto = proto.view_once_message.message   

        if proto.HasField("view_once_message_v2"):
            proto = proto.view_once_message_v2.message            

        if proto.HasField("document_with_caption_message"):
            proto = proto.document_with_caption_message.message   

        if proto.HasField("lottie_sticker_message"):
            proto = proto.lottie_sticker_message.message
            
        conversation = proto.conversation if proto.conversation else None
        image = self.proto_to_image(proto.image_message) if proto.HasField("image_message") else None
        contact = self.proto_to_contact(proto.contact_message) if proto.HasField("contact_message") else None
        location = self.proto_to_location(proto.location_message) if proto.HasField("location_message") else None
        extended_text = self.proto_to_extendedtext(proto.extended_text_message) if proto.HasField("extended_text_message") else None                            
        document = self.proto_to_document(proto.document_message) if proto.HasField("document_message") else None            
        audio = self.proto_to_audio(proto.audio_message) if proto.HasField("audio_message") else None
        video = self.proto_to_video(proto.video_message) if proto.HasField("video_message") else None
        sticker = self.proto_to_sticker(proto.sticker_message) if proto.HasField("sticker_message") else None
        reaction = self.proto_to_reaction(proto.reaction_message) if proto.HasField("reaction_message") else None
        template = self.proto_to_template(proto.template_message) if proto.HasField("template_message") else None
        buttons_response = self.proto_to_buttons_response(proto.buttons_response_message) if proto.HasField("buttons_response_message") else None
        poll_creation = self.proto_to_poll_creation(proto.pollCreationMessageV3,proto.message_context_info) if proto.HasField("pollCreationMessageV3") else None

        if proto.HasField("poll_update_message"):            
            poll_update = self.proto_to_poll_update(proto.poll_update_message,from_jid = from_jid,message_db=message_db)
        else:
            poll_update = None

        list_response = self.proto_to_list_response(proto.list_response_message) if proto.HasField("list_response_message") else None
        product = self.proto_to_product(proto.product_message) if proto.HasField("product_message") else None
        sender_key_distribution_message = self.proto_to_sender_key_distribution_message(
            proto.sender_key_distribution_message
        ) if proto.HasField("sender_key_distribution_message") else None
        protocol = self.proto_to_protocol(proto.protocol_message) if proto.HasField("protocol_message") else None

        return MessageAttributes(
            conversation=conversation,
            image=image,
            contact=contact,
            location=location,
            extended_text =extended_text,
            document= document,
            audio = audio,
            video = video,
            sticker = sticker,
            template = template,
            buttons_response = buttons_response,            
            list_response = list_response,
            poll_creation= poll_creation,
            poll_update = poll_update,
            reaction = reaction,
            product = product,
            sender_key_distribution_message = sender_key_distribution_message,
            protocol=protocol,            
        )



    def contact_to_proto(self, contact_attributes):
        contact_message = Message.ContactMessage()
        contact_message.display_name = contact_attributes.display_name
        contact_message.vcard = contact_attributes.vcard
        if contact_attributes.context_info is not None:
            contact_message.context_info.MergeFrom(self.contextinfo_to_proto(contact_attributes.context_info))
        return contact_message

    def proto_to_contact(self, proto):
        return ContactAttributes(
            proto.display_name,
            proto.vcard,
            self.proto_to_contextinfo(proto.context_info) if proto.HasField("context_info") else None
        )
    
    def location_to_proto(self, location_attributes):
        location_message = Message.LocationMessage()
        if location_attributes.degrees_latitude is not None:
            location_message.degrees_latitude = location_attributes.degrees_latitude
        if location_attributes.degrees_longitude is not None:
            location_message.degrees_longitude = location_attributes.degrees_longitude
        if location_attributes.name is not None:
            location_message.name = location_attributes.name
        if location_attributes.address is not None:
            location_message.address = location_attributes.address
        if location_attributes.url is not None:
            location_message.url = location_attributes.url
        if location_attributes.duration is not None:
            location_message.duration = location_attributes.duration
        if location_attributes.accuracy_in_meters is not None:
            location_message.accuracy_in_meters = location_attributes.accuracy_in_meters
        if location_attributes.speed_in_mps is not None:
            location_message.speed_in_mps = location_attributes.speed_in_mps
        if location_attributes.degrees_clockwise_from_magnetic_north is not None:
            location_message.degrees_clockwise_from_magnetic_north = \
                location_attributes.degrees_clockwise_from_magnetic_north
        if location_attributes.axolotl_sender_key_distribution_message is not None:
            location_message._axolotl_sender_key_distribution_message = \
                location_attributes.axolotl_sender_key_distribution_message
        if location_attributes.jpeg_thumbnail is not None:
            location_message.jpeg_thumbnail = location_attributes.jpeg_thumbnail
        return location_message


    def proto_to_location(self, proto):
        pass
        # return LocationAttributes(
        #     proto.degrees_latitude if proto.HasField("degrees_latitude") else None,
        #     proto.degrees_longitude if proto.HasField("degrees_longitude") else None,
        #     proto.name if proto.HasField("name") else None,
        #     proto.address if proto.HasField("address") else None,
        #     proto.url if proto.HasField("url") else None,
        #     proto.duration if proto.HasField("duration") else None,
        #     proto.accuracy_in_meters if proto.HasField("accuracy_in_meters") else None,
        #     proto.speed_in_mps if proto.HasField("speed_in_mps") else None,
        #     proto.degrees_clockwise_from_magnetic_north
        #     if proto.HasField("degrees_clockwise_from_magnetic_north") else None,
        #     proto.axolotl_sender_key_distribution_message
        #     if proto.HasField("axolotl_sender_key_distribution_message") else None,
        #     proto.jpeg_thumbnail if proto.HasField("jpeg_thumbnail") else None
        # )

    def poll_creation_to_proto(self,poll_creation_attr):
        poll_creation_mesage= Message.PollCreationMessage()
        poll_creation_mesage.name = poll_creation_attr.name

        for option_item in poll_creation_attr.options:
            option = Message.PollCreationMessage.Option()
            option.option_name = option_item

            poll_creation_mesage.options.extend([option])       
        
        poll_creation_mesage.selectable_options_count = 0 if poll_creation_attr.multi else 1
             
        return poll_creation_mesage


    def proto_to_poll_creation(self,proto,msg_context):

        options = []
        for item in proto.options:
            options.append(item.option_name)

        return PollCreationAttributes(
            name = proto.name,
            options = options,
            multi = False if proto.selectable_options_count==1 else True,            
            message_secret=msg_context.message_secret
        )   

    def proto_to_poll_update(self,proto,from_jid,message_db):
        
        options = PollUpdateAttributes.get_options_from_encrypted_content(proto,from_jid,message_db)        

        if options is None:
            return None
            
        return PollUpdateAttributes(
            msgid = proto.poll_creation_message_key.id,
            creator_jid = proto.poll_creation_message_key.remote_jid,
            voter_jid = from_jid,                            
            options = options         
        )                 
    

    def product_to_proto(self, product_attribute):
        
        product_message = Message.ProductMessage()
        product_message.business_owner_jid = product_attribute.business_owner_jid
        product_message.product.product_id = product_attribute.product_id
        product_message.product.title = product_attribute.title
        product_message.product.description=product_attribute.description        
        product_message.product.product_image_count = 1
        product_message.product.product_image.width = product_attribute.product_image.width
        product_message.product.product_image.height = product_attribute.product_image.height
        if product_attribute.product_image.jpeg_thumbnail is not None:
            product_message.product.product_image.jpeg_thumbnail = product_attribute.product_image.jpeg_thumbnail

        self.downloadablemedia_to_proto(product_attribute.product_image.downloadablemedia_attributes, product_message.product.product_image)

        return product_message
    def proto_to_product(self,proto):

        return ProductAttributes(
            product_image =  ImageAttributes(
                self.proto_to_downloadablemedia(proto.product.product_image),
                proto.product.product_image.width,proto.product.product_image.height,
                proto.product.product_image.caption if proto.product.product_image.HasField("caption") else None,
                proto.product.product_image.jpeg_thumbnail if proto.product.product_image.HasField("jpeg_thumbnail") else None
            ),
            title = proto.product.title,
            description = proto.product.description,
            product_id = proto.product.product_id,
            business_owner_jid = proto.business_owner_jid
        )


    def image_to_proto(self, image_attributes):

        image_message = Message.ImageMessage()
        image_message.width = image_attributes.width
        image_message.height = image_attributes.height
        if image_attributes.caption is not None:
            image_message.caption = image_attributes.caption
        if image_attributes.jpeg_thumbnail is not None:
            image_message.jpeg_thumbnail = image_attributes.jpeg_thumbnail

        return self.downloadablemedia_to_proto(image_attributes.downloadablemedia_attributes, image_message)

    def proto_to_image(self, proto):

        return ImageAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.width, proto.height,
            proto.caption if proto.HasField("caption") else None,
            proto.jpeg_thumbnail if proto.HasField("jpeg_thumbnail") else None
        )


    def proto_to_extendedtext(self, proto):

        logger.info(f"proto: {proto}")
                
        return ExtendedTextAttributes(
            text = proto.text if proto.HasField("text") else None,
            matched_text=proto.matched_text if proto.HasField("matched_text") else None,
            canonical_url=proto.canonical_url if proto.HasField("canonical_url") else None,
            description=proto.description if proto.HasField("description") else None,
            title=proto.title if proto.HasField("title") else None,
            jpeg_thumbnail=proto.jpeg_thumbnail if proto.HasField("jpeg_thumbnail") else None,            
            context_info=self.proto_to_contextinfo(proto.context_info) if proto.HasField("context_info") else None,
            text_argb=proto.text_argb if proto.HasField("text_argb") else None, 
            background_argb=proto.background_argb if proto.HasField("background_argb") else None, 
            font=proto.font if proto.HasField("font") else None, 
            preview_type=proto.preview_type if proto.HasField("preview_type") else None, 
            invite_link_group_type_v2=proto.invite_link_group_type_v2 if proto.HasField("invite_link_group_type_v2") else None,             
        )

    def proto_to_video(self, proto):
        return VideoAttributes(
            self.proto_to_downloadablemedia(proto),
            proto.width, proto.height, proto.seconds, proto.caption, proto.gif_playback,
            proto.jpeg_thumbnail, proto.gif_attribution,  proto.streaming_sidecar
        )
    def template_to_proto(self, template_attributes):
        # type: (TemplateAttributes) -> Message.TemplateMessage
        i = 0
        m = Message.TemplateMessage()        
        m.hydrated_template.hydrated_content_text=template_attributes["text"]
        m.template_id="988428568503979"
        m.hydrated_template.template_id = "988428568503979"
        for btn_item in template_attributes["buttons"]:
      
            button = HydratedTemplateButton()    
            
            if btn_item["type"]=="url":                
                button.url_button.display_text=btn_item["text"]
                button.url_button.url=btn_item["url"]
                button.index = i                
            if btn_item["type"]=="call":                
                button.call_button.display_text=btn_item["text"]
                button.call_button.phone_number=btn_item["phone"]
                button.index = i
            if btn_item["type"]=="quickreply":
                button.quick_reply_button.display_text=btn_item["text"]
                button.quick_reply_button.id=btn_item["id"]
                button.index = i

            m.hydrated_template.hydrated_buttons.extend([button])            
            i += 1
      
        return m  
    
    def list_to_proto(self,list_attribute):
        m = Message.ListMessage()   
        m.title = list_attribute.title
        m.button_text = list_attribute.button_text
        if list_attribute.description is not None:
            m.description = list_attribute.description 
        if list_attribute.footer is not None:
            m.footer_text = list_attribute.footer         

        i = 1
        for sec in list_attribute.list_content:
            section = Message.ListMessage.Section()
            section.title = sec["title"]            
            for row in sec["rows"]:
                r = Message.ListMessage.Row()
                r.title = row["title"]
                r.description = row["desc"]

                if "row_id" in row and row["row_id"] is not None:
                    r.row_id = row["row_id"]
                else:
                    #没有标识rowid，就用默认序号标记
                    r.row_id = str(i)

                i += 1
                section.rows.append(r)

            m.sections.append(section)
        
        m.list_type = 1

        return m
                   

                        
    def buttons_to_proto(self, buttons_attribute):
        m = Message.ButtonsMessage()   
        m.content_text = buttons_attribute.content

        if buttons_attribute.footer is not None:
            m.footer_text = buttons_attribute.footer 
            
        for btn_item in buttons_attribute.buttons:
            button = Message.ButtonsMessage.Button()
            button.button_id = btn_item["id"]
            button.button_text.display_text = btn_item["text"]
            button.type = 1
            m.buttons.extend([button]) 
            m.header_type = 1
        
        return m     
    def proto_to_buttons_response(self,proto):
        return ButtonsResponseAttributes(
            proto.selected_button_id, proto.selected_display_text, proto.type
        )

    def proto_to_list_response(self,proto):        
        return ListResponseAttributes(
            proto.single_select_reply.selected_row_id, proto.title, proto.list_type
        )        


    def protobytes_to_proto(self,protobytes):
        from ....proto.e2e_pb2 import Message
        m = Message()
        m.ParseFromString(protobytes)          
        return m
        
    def protobytes_to_message(self, protobytes,from_jid=None,message_db=None):
        m = self.protobytes_to_proto(protobytes)        
        return self.proto_to_message(m,from_jid,message_db)

    def message_to_protobytes(self, message):
        return self.message_to_proto(message).SerializeToString()