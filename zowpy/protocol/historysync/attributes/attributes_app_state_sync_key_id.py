"""
AppStateSyncKeyIdAttribute - ID de chave de sincronização de app state.
"""

from ....proto import e2e_pb2


class AppStateSyncKeyIdAttribute:
    """
    Atributo de ID de chave de sincronização de app state.
    """
    
    def __init__(self, key_id: bytes):
        """
        Inicializa ID de chave de app state sync.
        
        :param key_id: ID da chave (bytes)
        """
        self._key_id = key_id
    
    @property
    def key_id(self):
        """Obtém ID da chave."""
        return self._key_id
    
    @key_id.setter
    def key_id(self, value):
        """Define ID da chave."""
        self._key_id = value
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.AppStateSyncKeyId
        """
        pb_obj = e2e_pb2.AppStateSyncKeyId()
        
        if self._key_id is not None:
            pb_obj.key_id = self._key_id
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.AppStateSyncKeyId
        :return: AppStateSyncKeyIdAttribute
        """
        key_id = pb_obj.key_id if pb_obj.HasField("key_id") else None
        
        return AppStateSyncKeyIdAttribute(key_id=key_id)
    
    # Alias para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return AppStateSyncKeyIdAttribute.decode_from(pb_obj)

