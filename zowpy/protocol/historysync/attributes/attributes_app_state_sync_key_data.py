"""
AppStateSyncKeyDataAttribute - Dados de chave de sincronização de app state.
"""

from ....proto import e2e_pb2

from .attributes_app_state_sync_key_fingerprint import AppStateSyncKeyFingerprintAttribute


class AppStateSyncKeyDataAttribute:
    """
    Atributo de dados de chave de sincronização de app state.
    """
    
    def __init__(self, key_data: bytes, fingerprint: AppStateSyncKeyFingerprintAttribute, timestamp: int):
        """
        Inicializa dados de chave de app state sync.
        
        :param key_data: Dados da chave (bytes)
        :param fingerprint: AppStateSyncKeyFingerprintAttribute
        :param timestamp: Timestamp de criação (int64)
        """
        self._key_data = key_data
        self._fingerprint = fingerprint
        self._timestamp = timestamp
    
    @property
    def key_data(self):
        """Obtém dados da chave."""
        return self._key_data
    
    @key_data.setter
    def key_data(self, value):
        """Define dados da chave."""
        self._key_data = value
    
    @property
    def fingerprint(self):
        """Obtém fingerprint."""
        return self._fingerprint
    
    @fingerprint.setter
    def fingerprint(self, value):
        """Define fingerprint."""
        self._fingerprint = value
    
    @property
    def timestamp(self):
        """Obtém timestamp."""
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, value):
        """Define timestamp."""
        self._timestamp = value
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.AppStateSyncKeyData
        """
        pb_obj = e2e_pb2.AppStateSyncKeyData()
        
        if self._key_data is not None:
            pb_obj.key_data = self._key_data
        
        if self._fingerprint is not None:
            pb_obj.fingerprint.MergeFrom(self._fingerprint.encode())
        
        if self._timestamp is not None:
            pb_obj.timestamp = self._timestamp
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.AppStateSyncKeyData
        :return: AppStateSyncKeyDataAttribute
        """
        key_data = pb_obj.key_data if pb_obj.HasField("key_data") else None
        fingerprint = None
        if pb_obj.HasField("fingerprint"):
            fingerprint = AppStateSyncKeyFingerprintAttribute.decode_from(pb_obj.fingerprint)
        timestamp = pb_obj.timestamp if pb_obj.HasField("timestamp") else None
        
        return AppStateSyncKeyDataAttribute(
            key_data=key_data,
            fingerprint=fingerprint,
            timestamp=timestamp
        )
    
    # Alias para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return AppStateSyncKeyDataAttribute.decode_from(pb_obj)

