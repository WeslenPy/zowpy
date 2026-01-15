"""
PastParticipantAttribute - Atributo de participante passado.
"""

from ....proto import e2e_pb2


class PastParticipantAttribute:
    """
    Atributo de participante passado (que saiu do grupo).
    """
    
    def __init__(self, user_jid, leave_reason, leave_ts):
        """
        Inicializa atributo de participante passado.
        
        :param user_jid: JID do usuário
        :param leave_reason: Razão da saída
        :param leave_ts: Timestamp da saída
        """
        self.userJid = user_jid
        self.leaveReason = leave_reason
        self.leaveTs = leave_ts
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.PastParticipant
        """
        pb_obj = e2e_pb2.PastParticipant()
        
        if self.userJid is not None:
            pb_obj.userJid = self.userJid
        
        if self.leaveReason is not None:
            pb_obj.leaveReason = self.leaveReason
        
        if self.leaveTs is not None:
            pb_obj.leaveTs = self.leaveTs
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.PastParticipant
        :return: PastParticipantAttribute
        """
        user_jid = pb_obj.userJid if pb_obj.HasField("userJid") else None
        leave_reason = pb_obj.leaveReason if pb_obj.HasField("leaveReason") else None
        leave_ts = pb_obj.leaveTs if pb_obj.HasField("leaveTs") else None
        
        return PastParticipantAttribute(
            user_jid=user_jid,
            leave_reason=leave_reason,
            leave_ts=leave_ts
        )
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return PastParticipantAttribute.decode_from(pb_obj)

