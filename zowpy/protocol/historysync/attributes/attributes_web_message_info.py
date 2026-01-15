"""
WebMessageInfoAttribute - Informação de mensagem web.
"""

from ....proto import e2e_pb2

from .attributes_message_key import MessageKeyAttribute


class WebMessageInfoAttribute:
    """
    Atributo de informação de mensagem web.
    
    Usado principalmente para status (statusV3Messages).
    """
    
    def __init__(self, key: MessageKeyAttribute):
        """
        Inicializa informação de mensagem web.
        
        :param key: MessageKeyAttribute identificando a mensagem
        """
        self.key = key
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.WebMessageInfo
        """
        pb_obj = e2e_pb2.WebMessageInfo()
        
        if self.key is not None:
            pb_obj.key.MergeFrom(self.key.encode())
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.WebMessageInfo
        :return: WebMessageInfoAttribute
        """
        key = MessageKeyAttribute.decode_from(pb_obj.key)
        return WebMessageInfoAttribute(key=key)
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return WebMessageInfoAttribute.decode_from(pb_obj)

