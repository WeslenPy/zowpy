"""
PastParticipantsAttribute - Atributo de participantes passados.
"""

from ....proto import e2e_pb2

from .attributes_past_participant import PastParticipantAttribute


class PastParticipantsAttribute:
    """
    Atributo de participantes passados de um grupo.
    """
    
    def __init__(self, group_jid, past_participants):
        """
        Inicializa atributo de participantes passados.
        
        :param group_jid: JID do grupo
        :param past_participants: Lista de PastParticipantAttribute
        """
        self.groupJid = group_jid
        self.pastParticipants = past_participants or []
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.PastParticipants
        """
        pb_obj = e2e_pb2.PastParticipants()
        
        if self.groupJid is not None:
            pb_obj.groupJid = self.groupJid
        
        for item in self.pastParticipants:
            pb_obj.pastParticipants.append(item.encode())
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.PastParticipants
        :return: PastParticipantsAttribute
        """
        group_jid = pb_obj.groupJid if pb_obj.HasField("groupJid") else None
        
        past_participants = []
        for item in pb_obj.pastParticipants:
            past_participants.append(PastParticipantAttribute.decode_from(item))
        
        return PastParticipantsAttribute(
            group_jid=group_jid,
            past_participants=past_participants
        )
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return PastParticipantsAttribute.decode_from(pb_obj)

