"""
AppStateSyncKeyFingerprintAttribute - Fingerprint de chave de sincronização de app state.
"""

from ....proto import e2e_pb2


class AppStateSyncKeyFingerprintAttribute:
    """
    Atributo de fingerprint de chave de sincronização de app state.
    """
    
    def __init__(self, raw_id: int, current_index: int, device_indexes: list):
        """
        Inicializa fingerprint de chave de app state sync.
        
        :param raw_id: ID raw (uint32)
        :param current_index: Índice atual (uint32)
        :param device_indexes: Lista de índices de dispositivos (repeated uint32)
        """
        self._raw_id = raw_id
        self._current_index = current_index
        self._device_indexes = device_indexes or []
    
    @property
    def raw_id(self):
        """Obtém ID raw."""
        return self._raw_id
    
    @raw_id.setter
    def raw_id(self, value):
        """Define ID raw."""
        self._raw_id = value
    
    @property
    def current_index(self):
        """Obtém índice atual."""
        return self._current_index
    
    @current_index.setter
    def current_index(self, value):
        """Define índice atual."""
        self._current_index = value
    
    @property
    def device_indexes(self):
        """Obtém lista de índices de dispositivos."""
        return self._device_indexes
    
    @device_indexes.setter
    def device_indexes(self, value):
        """Define lista de índices de dispositivos."""
        self._device_indexes = value
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.AppStateSyncKeyFingerprint
        """
        pb_obj = e2e_pb2.AppStateSyncKeyFingerprint()
        
        if self._raw_id is not None:
            pb_obj.raw_id = self._raw_id
        
        if self._current_index is not None:
            pb_obj.current_index = self._current_index
        
        if self._device_indexes:
            pb_obj.device_indexes.extend(self._device_indexes)
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.AppStateSyncKeyFingerprint
        :return: AppStateSyncKeyFingerprintAttribute
        """
        raw_id = pb_obj.raw_id if pb_obj.HasField("raw_id") else None
        current_index = pb_obj.current_index if pb_obj.HasField("current_index") else None
        device_indexes = list(pb_obj.device_indexes) if pb_obj.device_indexes else []
        
        return AppStateSyncKeyFingerprintAttribute(
            raw_id=raw_id,
            current_index=current_index,
            device_indexes=device_indexes
        )
    
    # Alias para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return AppStateSyncKeyFingerprintAttribute.decode_from(pb_obj)

