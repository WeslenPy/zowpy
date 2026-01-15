"""
AppStateSyncKeyAttribute - Chave de sincronização de app state.
"""

from ....proto import e2e_pb2

from .attributes_app_state_sync_key_id import AppStateSyncKeyIdAttribute
from .attributes_app_state_sync_key_data import AppStateSyncKeyDataAttribute


class AppStateSyncKeyAttribute:
    """
    Atributo de chave de sincronização de app state.
    """
    
    def __init__(self, key_id: AppStateSyncKeyIdAttribute, key_data: AppStateSyncKeyDataAttribute):
        """
        Inicializa chave de app state sync.
        
        :param key_id: AppStateSyncKeyIdAttribute
        :param key_data: AppStateSyncKeyDataAttribute
        """
        self._key_id = key_id
        self._key_data = key_data
    
    @property
    def key_id(self):
        """Obtém ID da chave."""
        return self._key_id
    
    @key_id.setter
    def key_id(self, value):
        """Define ID da chave."""
        self._key_id = value
    
    @property
    def key_data(self):
        """Obtém dados da chave."""
        return self._key_data
    
    @key_data.setter
    def key_data(self, value):
        """Define dados da chave."""
        self._key_data = value
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.AppStateSyncKey
        """
        pb_obj = e2e_pb2.AppStateSyncKey()
        
        if self._key_id is not None:
            pb_obj.key_id.MergeFrom(self._key_id.encode())
        
        if self._key_data is not None:
            pb_obj.key_data.MergeFrom(self._key_data.encode())
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.AppStateSyncKey
        :return: AppStateSyncKeyAttribute
        """
        key_id = None
        if pb_obj.HasField("key_id"):
            key_id = AppStateSyncKeyIdAttribute.decode_from(pb_obj.key_id)
        
        key_data = None
        if pb_obj.HasField("key_data"):
            key_data = AppStateSyncKeyDataAttribute.decode_from(pb_obj.key_data)
        
        return AppStateSyncKeyAttribute(key_id=key_id, key_data=key_data)
    
    # Alias para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return AppStateSyncKeyAttribute.decode_from(pb_obj)

