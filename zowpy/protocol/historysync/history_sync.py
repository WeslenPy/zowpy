"""
HistorySync - Classe principal para sincronização de histórico.

Implementa os protocolos de history sync para multi-device do WhatsApp.
"""

import zlib
from typing import Optional, List
from loguru import logger

from .attributes import (
    HistorySyncAttribute,
    HistorySyncNotificationAttribute,
    ConversationAttribute,
    WebMessageInfoAttribute,
    PushnameAttribute,
    PastParticipantsAttribute,
)


def compress(data: bytes) -> bytes:
    """
    Comprime dados usando zlib.
    
    :param data: Dados não comprimidos
    :return: Dados comprimidos
    """
    compressor = zlib.compressobj()
    compressed = compressor.compress(data)
    compressed += compressor.flush()
    return compressed


def decompress(data: bytes) -> bytes:
    """
    Descomprime dados usando zlib.
    
    :param data: Dados comprimidos
    :return: Dados descomprimidos
    """
    decompressor = zlib.decompressobj()
    decompressed = decompressor.decompress(data)
    decompressed += decompressor.flush()
    return decompressed


class HistorySync:
    """
    Classe principal para criação de mensagens de history sync.
    
    Usado para sincronizar histórico de conversas, status, pushnames, etc.
    entre dispositivos no WhatsApp multi-device.
    """
    
    def __init__(self, media_conn=None, to_jid: Optional[str] = None):
        """
        Inicializa HistorySync.
        
        :param media_conn: Resultado de RequestMediaConn (para upload)
        :param to_jid: JID de destino (companion device)
        """
        self.media_conn = media_conn
        self.to_jid = to_jid
    
    def create_sync_message(
        self,
        history_sync_attrs: HistorySyncAttribute,
        to_jid: Optional[str] = None,
        sync_type: Optional[str] = None
    ) -> dict:
        """
        Cria mensagem de history sync.
        
        :param history_sync_attrs: Atributos de history sync
        :param to_jid: JID de destino (None usa self.to_jid)
        :param sync_type: Tipo de sync (None usa o tipo dos atributos)
        :return: Dict com dados da mensagem (para criar ProtocolMessage)
        """
        # Comprime os dados de history sync
        pb_obj = history_sync_attrs.encode()
        sync_bytes = compress(pb_obj.SerializeToString())
        
        # Se não tiver media_conn, retorna apenas os dados comprimidos
        # (o upload será feito separadamente)
        if self.media_conn is None:
            logger.warning("media_conn não fornecido, retornando dados sem upload")
            return {
                "sync_data": sync_bytes,
                "sync_type": sync_type or history_sync_attrs.syncType,
                "to_jid": to_jid or self.to_jid,
            }
        
        # TODO: Implementar upload de mídia quando DownloadableMediaMessageAttributes estiver disponível
        # Por enquanto, retorna estrutura básica
        logger.debug("History sync message criada (upload de mídia pendente)")
        
        return {
            "sync_data": sync_bytes,
            "sync_type": sync_type or history_sync_attrs.syncType,
            "to_jid": to_jid or self.to_jid,
            "media_conn": self.media_conn,
        }
    
    # ========== Métodos de conveniência ==========
    
    def create_non_blocking_data_message(
        self,
        to_jid: Optional[str] = None,
        past_participants: Optional[List] = None
    ) -> dict:
        """
        Cria mensagem de non-blocking data sync.
        
        :param to_jid: JID de destino
        :param past_participants: Lista de PastParticipantsAttribute
        :return: Dict com dados da mensagem
        """
        return self.create_sync_message(
            history_sync_attrs=HistorySyncAttribute(
                sync_type=HistorySyncAttribute.NON_BLOCKING_DATA,
                past_participants=past_participants or []
            ),
            to_jid=to_jid,
            sync_type=None
        )
    
    def create_initial_status_v3_message(
        self,
        to_jid: Optional[str] = None,
        status_v3_messages: Optional[List[WebMessageInfoAttribute]] = None
    ) -> dict:
        """
        Cria mensagem de sincronização inicial de status V3.
        
        :param to_jid: JID de destino
        :param status_v3_messages: Lista de WebMessageInfoAttribute
        :return: Dict com dados da mensagem
        """
        return self.create_sync_message(
            history_sync_attrs=HistorySyncAttribute(
                sync_type=HistorySyncAttribute.INITIAL_STATUS_V3,
                status_v3_messages=status_v3_messages or []
            ),
            to_jid=to_jid
        )
    
    def create_push_name_message(
        self,
        to_jid: Optional[str] = None,
        pushnames: Optional[List[PushnameAttribute]] = None
    ) -> dict:
        """
        Cria mensagem de sincronização de pushnames.
        
        :param to_jid: JID de destino
        :param pushnames: Lista de PushnameAttribute
        :return: Dict com dados da mensagem
        """
        return self.create_sync_message(
            history_sync_attrs=HistorySyncAttribute(
                sync_type=HistorySyncAttribute.PUSH_NAME,
                pushnames=pushnames or []
            ),
            to_jid=to_jid
        )
    
    def create_recent_message(
        self,
        to_jid: Optional[str] = None,
        conversations: Optional[List[ConversationAttribute]] = None
    ) -> dict:
        """
        Cria mensagem de sincronização de conversas recentes.
        
        :param to_jid: JID de destino
        :param conversations: Lista de ConversationAttribute
        :return: Dict com dados da mensagem
        """
        return self.create_sync_message(
            history_sync_attrs=HistorySyncAttribute(
                sync_type=HistorySyncAttribute.RECENT,
                conversations=conversations or []
            ),
            to_jid=to_jid
        )
    
    def create_initial_bootstrap_message(
        self,
        to_jid: Optional[str] = None,
        conversations: Optional[List[ConversationAttribute]] = None
    ) -> dict:
        """
        Cria mensagem de sincronização inicial (bootstrap).
        
        :param to_jid: JID de destino
        :param conversations: Lista de ConversationAttribute
        :return: Dict com dados da mensagem
        """
        return self.create_sync_message(
            history_sync_attrs=HistorySyncAttribute(
                sync_type=HistorySyncAttribute.INITIAL_BOOTSTRAP,
                conversations=conversations or []
            ),
            to_jid=to_jid
        )
    
    @staticmethod
    def decode_sync_data(compressed_data: bytes) -> HistorySyncAttribute:
        """
        Decodifica dados de history sync comprimidos.
        
        :param compressed_data: Dados comprimidos
        :return: HistorySyncAttribute
        """
        from ...proto import e2e_pb2
        
        # Descomprime
        decompressed = decompress(compressed_data)
        
        # Parse protobuf
        pb_obj = e2e_pb2.HistorySync()
        pb_obj.ParseFromString(decompressed)
        
        # Decodifica atributo
        return HistorySyncAttribute.decode_from(pb_obj)

