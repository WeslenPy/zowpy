"""
AppStateSyncKeyShareAttribute - Compartilhamento de chaves de sincronização de app state.
"""

from ....proto import e2e_pb2

from .attributes_app_state_sync_key import AppStateSyncKeyAttribute


class AppStateSyncKeyShareAttribute:
    """
    Atributo de compartilhamento de chaves de sincronização de app state.
    """
    
    def __init__(self, keys: list):
        """
        Inicializa compartilhamento de chaves de app state sync.
        
        :param keys: Lista de AppStateSyncKeyAttribute
        """
        self._keys = keys or []
    
    @property
    def keys(self):
        """Obtém lista de chaves."""
        return self._keys
    
    @keys.setter
    def keys(self, value):
        """Define lista de chaves."""
        self._keys = value
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.AppStateSyncKeyShare
        """
        pb_obj = e2e_pb2.AppStateSyncKeyShare()
        
        for key in self._keys:
            pb_obj.keys.append(key.encode())
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.AppStateSyncKeyShare
        :return: AppStateSyncKeyShareAttribute
        """
        keys = []
        for item in pb_obj.keys:
            keys.append(AppStateSyncKeyAttribute.decode_from(item))
        
        return AppStateSyncKeyShareAttribute(keys=keys)
    
    # Alias para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return AppStateSyncKeyShareAttribute.decode_from(pb_obj)

