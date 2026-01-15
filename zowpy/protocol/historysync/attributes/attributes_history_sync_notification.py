"""
HistorySyncNotificationAttribute - Notificação de sincronização de histórico.
"""

from ....proto import e2e_pb2


class HistorySyncNotificationAttribute:
    """
    Atributo de notificação de history sync.
    
    Contém informações sobre o arquivo de mídia que contém os dados
    de sincronização comprimidos e criptografados.
    """
    
    def __init__(
        self,
        media_sha256=None,
        media_encrypted_sha256=None,
        media_key=None,
        media_direct_path=None,
        media_size=None,
        sync_type=None
    ):
        """
        Inicializa notificação de history sync.
        
        :param media_sha256: SHA256 do arquivo de mídia
        :param media_encrypted_sha256: SHA256 do arquivo criptografado
        :param media_key: Chave de mídia para descriptografar
        :param media_direct_path: Caminho direto do arquivo
        :param media_size: Tamanho do arquivo
        :param sync_type: Tipo de sincronização
        """
        self.mediaSha256 = media_sha256
        self.mediaEncryptedSha256 = media_encrypted_sha256
        self.mediaKey = media_key
        self.mediaDirectPath = media_direct_path
        self.mediaSize = media_size
        self.syncType = sync_type
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.HistorySyncNotification
        """
        pb_obj = e2e_pb2.HistorySyncNotification()
        
        if self.mediaSha256 is not None:
            pb_obj.fileSha256 = self.mediaSha256
        
        if self.mediaEncryptedSha256 is not None:
            pb_obj.fileEncSha256 = self.mediaEncryptedSha256
        
        if self.mediaKey is not None:
            pb_obj.mediaKey = self.mediaKey
        
        if self.mediaDirectPath is not None:
            pb_obj.directPath = self.mediaDirectPath
        
        if self.mediaSize is not None:
            pb_obj.fileLength = self.mediaSize
        
        if self.syncType is not None:
            pb_obj.syncType = self.syncType
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.HistorySyncNotification
        :return: HistorySyncNotificationAttribute
        """
        media_sha256 = pb_obj.fileSha256 if pb_obj.HasField("fileSha256") else None
        media_encrypted_sha256 = pb_obj.fileEncSha256 if pb_obj.HasField("fileEncSha256") else None
        media_key = pb_obj.mediaKey if pb_obj.HasField("mediaKey") else None
        media_direct_path = pb_obj.directPath if pb_obj.HasField("directPath") else None
        media_size = pb_obj.fileLength if pb_obj.HasField("fileLength") else None
        sync_type = pb_obj.syncType if pb_obj.HasField("syncType") else None
        
        return HistorySyncNotificationAttribute(
            media_sha256=media_sha256,
            media_encrypted_sha256=media_encrypted_sha256,
            media_key=media_key,
            media_direct_path=media_direct_path,
            media_size=media_size,
            sync_type=sync_type
        )
    
    # Aliases para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return HistorySyncNotificationAttribute.decode_from(pb_obj)

