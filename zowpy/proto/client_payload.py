"""
Protobuf ClientPayload - Builder assíncrono para ClientPayload.

Estilo whatsmeow: builder centralizado para ClientPayload do handshake.
"""

import asyncio
from typing import Optional, Dict, Any
from loguru import logger

from .helpers import serialize_async
from ..noise.config import ClientConfig, UserAgentConfig, AppVersionConfig
from ..noise.proto import wa5_pb2


class AsyncClientPayloadBuilder:
    """
    Builder assíncrono para ClientPayload.
    Constrói payload do cliente para handshake.
    """
    
    @staticmethod
    async def build(
        client_config: ClientConfig,
        session_id: Optional[int] = None,
        connect_reason: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Constrói ClientPayload de forma assíncrona.
        
        :param client_config: Configuração do cliente
        :param session_id: ID da sessão
        :param connect_reason: Razão da conexão
        :param kwargs: Outros parâmetros
        :return: Bytes serializados
        """
        if wa5_pb2 is None:
            raise RuntimeError("ClientPayload protobuf não disponível")
        
        payload = wa5_pb2.ClientPayload()
        
        # Username
        payload.username = client_config.username
        
        # Passive
        payload.passive = client_config.passive
        
        # UserAgent
        useragent = client_config.useragent
        payload.user_agent.platform = useragent.platform
        payload.user_agent.app_version.primary = useragent.app_version.primary
        payload.user_agent.app_version.secondary = useragent.app_version.secondary
        payload.user_agent.app_version.tertiary = useragent.app_version.tertiary
        payload.user_agent.app_version.quaternary = useragent.app_version.quaternary
        payload.user_agent.mcc = useragent.mcc
        payload.user_agent.mnc = useragent.mnc
        payload.user_agent.os_version = useragent.os_version
        payload.user_agent.manufacturer = useragent.manufacturer
        payload.user_agent.device = useragent.device
        payload.user_agent.os_build_number = useragent.os_build_number
        payload.user_agent.phone_id = useragent.phone_id
        payload.user_agent.locale_language_iso_639_1 = useragent.locale_lang
        payload.user_agent.locale_country_iso_3166_1_alpha_2 = useragent.locale_country
        payload.user_agent.device_exp_id = useragent.device_exp_id
        payload.user_agent.device_type = useragent.device_type
        payload.user_agent.device_model_type = useragent.device_model_type
        
        # Pushname
        payload.push_name = client_config.pushname
        
        # Session ID
        if session_id is not None:
            payload.session_id = session_id
        
        # Short connect
        payload.short_connect = client_config.short_connect
        
        # Connect reason
        if connect_reason:
            # Mapeia para enum se necessário
            pass
        
        # Outros campos opcionais
        if "shards" in kwargs:
            payload.shards.extend(kwargs["shards"])
        
        return await serialize_async(payload)

