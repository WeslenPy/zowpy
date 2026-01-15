"""
MessageKeyAttribute - Chave de mensagem.
"""

from ....proto import protocol_pb2
from ....proto import e2e_pb2


class MessageKeyAttribute:
    """
    Atributo de chave de mensagem.
    
    Identifica unicamente uma mensagem no WhatsApp.
    """
    
    def __init__(
        self,
        remote_jid=None,
        from_me=None,
        id=None,
        participant=None
    ):
        """
        Inicializa chave de mensagem.
        
        :param remote_jid: JID remoto (destinatário/remetente)
        :param from_me: Se True, mensagem foi enviada por mim
        :param id: ID da mensagem
        :param participant: Participante (para grupos)
        """
        self.remoteJid = remote_jid
        self.fromMe = from_me
        self.id = id
        self.participant = participant
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: protocol_pb2.MessageKey
        """
        pb_obj = protocol_pb2.MessageKey()
        
        if self.remoteJid is not None:
            pb_obj.remote_jid = self.remoteJid
        
        if self.fromMe is not None:
            pb_obj.from_me = self.fromMe
        
        if self.id is not None:
            pb_obj.id = self.id
        
        if self.participant is not None:
            pb_obj.participant = self.participant
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: protocol_pb2.MessageKey
        :return: MessageKeyAttribute
        """
        remote_jid = pb_obj.remote_jid if pb_obj.HasField("remote_jid") else None
        from_me = pb_obj.from_me if pb_obj.HasField("from_me") else None
        id = pb_obj.id if pb_obj.HasField("id") else None
        participant = pb_obj.participant if pb_obj.HasField("participant") else None
        
        return MessageKeyAttribute(
            remote_jid=remote_jid,
            from_me=from_me,
            id=id,
            participant=participant
        )
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return MessageKeyAttribute.decode_from(pb_obj)

