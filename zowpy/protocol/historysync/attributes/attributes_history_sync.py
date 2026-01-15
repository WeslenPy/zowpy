"""
HistorySyncAttribute - Atributo principal de sincronização de histórico.
"""

from ....proto import e2e_pb2

from .attributes_conversation import ConversationAttribute
from .attributes_past_participants import PastParticipantsAttribute
from .attributes_web_message_info import WebMessageInfoAttribute
from .attributes_pushname import PushnameAttribute


class HistorySyncAttribute:
    """
    Atributo de sincronização de histórico.
    
    Representa diferentes tipos de sincronização:
    - INITIAL_BOOTSTRAP: Sincronização inicial completa
    - INITIAL_STATUS_V3: Sincronização inicial de status
    - FULL: Sincronização completa
    - RECENT: Sincronização de conversas recentes
    - PUSH_NAME: Sincronização de nomes de push
    - NON_BLOCKING_DATA: Dados não bloqueantes
    - ON_DEMAND: Sincronização sob demanda
    """
    
    INITIAL_BOOTSTRAP = 0
    INITIAL_STATUS_V3 = 1
    FULL = 2
    RECENT = 3
    PUSH_NAME = 4
    NON_BLOCKING_DATA = 5
    ON_DEMAND = 6
    
    def __init__(
        self,
        sync_type: int,
        conversations=None,
        past_participants=None,
        status_v3_messages=None,
        pushnames=None
    ):
        """
        Inicializa atributo de history sync.
        
        :param sync_type: Tipo de sincronização (constantes acima)
        :param conversations: Lista de ConversationAttribute
        :param past_participants: Lista de PastParticipantsAttribute
        :param status_v3_messages: Lista de WebMessageInfoAttribute (status)
        :param pushnames: Lista de PushnameAttribute
        """
        self.syncType = sync_type
        self.conversations = conversations or []
        self.pastParticipants = past_participants or []
        self.statusV3Messages = status_v3_messages or []
        self.pushnames = pushnames or []
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.HistorySync
        """
        pb_obj = e2e_pb2.HistorySync()
        
        if self.syncType is not None:
            pb_obj.syncType = self.syncType
        
        if self.conversations:
            for item in self.conversations:
                pb_obj.conversations.append(item.encode())
        
        if self.pastParticipants:
            for item in self.pastParticipants:
                pb_obj.pastParticipants.append(item.encode())
        
        if self.statusV3Messages:
            for item in self.statusV3Messages:
                pb_obj.statusV3Messages.append(item.encode())
        
        if self.pushnames:
            for item in self.pushnames:
                pb_obj.pushnames.append(item.encode())
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.HistorySync
        :return: HistorySyncAttribute
        """
        sync_type = pb_obj.syncType if pb_obj.HasField("syncType") else None
        
        conversations = []
        for item in pb_obj.conversations:
            conversations.append(ConversationAttribute.decode_from(item))
        
        past_participants = []
        for item in pb_obj.pastParticipants:
            past_participants.append(PastParticipantsAttribute.decode_from(item))
        
        status_v3_messages = []
        for item in pb_obj.statusV3Messages:
            status_v3_messages.append(WebMessageInfoAttribute.decode_from(item))
        
        pushnames = []
        for item in pb_obj.pushnames:
            pushnames.append(PushnameAttribute.decode_from(item))
        
        return HistorySyncAttribute(
            sync_type=sync_type,
            conversations=conversations,
            past_participants=past_participants,
            status_v3_messages=status_v3_messages,
            pushnames=pushnames
        )
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return HistorySyncAttribute.decode_from(pb_obj)

