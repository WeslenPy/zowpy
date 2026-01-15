"""
ConversationAttribute - Atributo de conversa.
"""

from ....proto import e2e_pb2


class ConversationAttribute:
    """
    Atributo de conversa para history sync.
    """
    
    def __init__(self, id: str):
        """
        Inicializa atributo de conversa.
        
        :param id: ID da conversa (JID)
        """
        self.id = id
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.Conversation
        """
        pb_obj = e2e_pb2.Conversation()
        
        if self.id is not None:
            pb_obj.id = self.id
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.Conversation
        :return: ConversationAttribute
        """
        id = pb_obj.id if pb_obj.HasField("id") else None
        
        return ConversationAttribute(id=id)
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return ConversationAttribute.decode_from(pb_obj)

