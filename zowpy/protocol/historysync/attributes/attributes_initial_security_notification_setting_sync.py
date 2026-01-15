"""
InitialSecurityNotificationSettingSyncAttribute - Sincronização inicial de configuração de notificação de segurança.
"""

from ....proto import e2e_pb2


class InitialSecurityNotificationSettingSyncAttribute:
    """
    Atributo de sincronização inicial de configuração de notificação de segurança.
    """
    
    def __init__(self, security_notification_enabled: bool = True):
        """
        Inicializa sincronização de configuração de segurança.
        
        :param security_notification_enabled: Se True, notificações de segurança estão habilitadas
        """
        self._security_notification_enabled = security_notification_enabled
    
    @property
    def security_notification_enabled(self):
        """Obtém se notificações de segurança estão habilitadas."""
        return self._security_notification_enabled
    
    @security_notification_enabled.setter
    def security_notification_enabled(self, value):
        """Define se notificações de segurança estão habilitadas."""
        self._security_notification_enabled = value
    
    def encode(self):
        """
        Codifica para protobuf.
        
        :return: e2e_pb2.InitialSecurityNotificationSettingSync
        """
        pb_obj = e2e_pb2.InitialSecurityNotificationSettingSync()
        
        if self._security_notification_enabled is not None:
            pb_obj.security_notification_enabled = self._security_notification_enabled
        
        return pb_obj
    
    @staticmethod
    def decode_from(pb_obj):
        """
        Decodifica de protobuf.
        
        :param pb_obj: e2e_pb2.InitialSecurityNotificationSettingSync
        :return: InitialSecurityNotificationSettingSyncAttribute
        """
        security_notification_enabled = (
            pb_obj.security_notification_enabled 
            if pb_obj.HasField("security_notification_enabled") 
            else True
        )
        
        return InitialSecurityNotificationSettingSyncAttribute(
            security_notification_enabled=security_notification_enabled
        )
    
    # Alias para compatibilidade com zowsuplib
    @staticmethod
    def decodeFrom(pb_obj):
        """Alias para decode_from (compatibilidade)."""
        return InitialSecurityNotificationSettingSyncAttribute.decode_from(pb_obj)

