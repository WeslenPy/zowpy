"""
PushnameAttribute - Atributo de nome de push.
"""

from ....proto import e2e_pb2


class PushnameAttribute:
    """
    Atributo de nome de push (nome exibido).
    """
    
    def __init__(self, id=None, pushname=None):
        """
        Inicializa atributo de pushname.
        
        :param id: ID do usuário (JID)
        :param pushname: Nome de push (nome exibido)
        """
        self.id = id
        self.pushname = pushname
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.Pushname
        """
        pb_obj = e2e_pb2.Pushname()
        
        if self.id is not None:
            pb_obj.id = self.id
        
        if self.pushname is not None:
            pb_obj.pushname = self.pushname
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.Pushname
        :return: PushnameAttribute
        """
        id = pb_obj.id if pb_obj.HasField("id") else None
        pushname = pb_obj.pushname if pb_obj.HasField("pushname") else None
        
        return PushnameAttribute(id=id, pushname=pushname)
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return PushnameAttribute.decode_from(pb_obj)

