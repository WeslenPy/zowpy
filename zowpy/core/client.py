"""
WhatsApp Client V2 - Cliente com fluxo linear assíncrono.

Baseado no zowsuplib, mas totalmente assíncrono e sem eventos complexos.
Fluxo direto: conexão → handshake → autenticação.
"""

import asyncio
import base64
import json
import random
import time
from typing import Optional, Dict, Any, Tuple, List, Union
from loguru import logger

from zowpy.db.config.engine import AsyncSessionMaker
from zowpy.db.factory import AxolotlManagerFactory
from zowpy.db.models import Account
from zowpy.profile.profile import AsyncProfile
from zowpy.config.v1.config import Config
from zowpy.utils.tools import WATools
from zowpy.config.bot_env import BotEnv
from zowpy.config.network import NetworkConfig, ProxyConfig

from .connection import AsyncConnection, ConnectionError
from .bridge import TCPStreamBridge
from .store import AsyncStateStore
from .events import AsyncEventEmitter
from ..noise.stream import AsyncSegmentedStream, StreamCancelledError
from ..noise.handshake import AsyncWAHandshake, HandshakeFailedException
from ..noise.config import ClientConfig
from ..noise.transport import AsyncWANoiseTransport
from ..noise.structs import KeyPair, PublicKey
from ..protocol.coder import AsyncCoder
from ..protocol.messages import AsyncMessageHandler
from ..protocol.acks import AsyncAcksHandler
from ..protocol.receipts import AsyncReceiptHandler
from ..protocol.presence import AsyncPresenceHandler
from ..protocol.auth import AsyncAuthHandler
from ..protocol.structs import ProtocolNode
from ..db.manager import AxolotlManager
from ..utils.jid import normalize, to_whatsapp_jid
from ..axolotl.protocol.whispermessage import WhisperMessage
from ..axolotl.protocol.prekeywhispermessage import PreKeyWhisperMessage

# Nova arquitetura de processors
from .processors.router import NodeRouter
from .processors.message import MessageProcessor
from .processors.receipt import ReceiptProcessor
from .processors.ack import AckProcessor
from .processors.presence import PresenceProcessor
from .processors.iq import IQProcessor
from .processors.notification import NotificationProcessor
from .processors.group import GroupProcessor
from .processors.stream_error import StreamErrorProcessor
from .processors.iq_response import IQResponseProcessor
from .encryption.receiver import EncryptionReceiver
from .encryption.sender import EncryptionSender
from .builders.message_builder import MessageBuilder
from .builders.enc_entity import EncEntity
from .builders.encrypted_message_builder import EncryptedMessageBuilder
from ..proto.messages import AsyncMessageParser

# Handlers públicos
from .handlers.group_handler import GroupHandler
from .handlers.contact_handler import ContactHandler
from .handlers.presence_handler import PresenceHandler
from .handlers.profile_handler import ProfileHandler
from .handlers.integrity_handler import IntegrityHandler

# Builders
from .builders.prekey_builder import PrekeyBuilder

# Imports para _get_keys_for_recipient
import sys
import binascii
from ..axolotl.state.prekeybundle import PreKeyBundle
from ..axolotl.identitykey import IdentityKey
from ..axolotl.ecc.curve import Curve
from ..axolotl.ecc.djbec import DjbECPublicKey
from ..axolotl import exceptions
from ..utils.constants import YowConstants


class AuthenticationError(Exception):
    """Erro de autenticação"""
    pass


class WhatsAppClient:
    """
    Cliente WhatsApp com fluxo linear assíncrono.
    
    Baseado no zowsuplib, mas totalmente assíncrono e sem eventos complexos.
    Fluxo direto: conexão → handshake → autenticação.
    """
    
    def __init__(
        self,
        account_id: str,
        endpoint: Tuple[str, int] = None,
        session_maker: Optional[AsyncSessionMaker] = None,
        device_config=None,
        proxy: Optional[Dict[str, any]] = None,
    ):
        """
        Inicializa cliente WhatsApp.
        
        Args:
            account_id: ID da conta (número de telefone)
            endpoint: Endpoint TCP do WhatsApp (host, port)
            session_maker: AsyncSessionMaker
            device_config: Configuração do dispositivo
            proxy: Configuração de proxy (opcional)
        """
        self.account_id = normalize(account_id)
        self.endpoint = endpoint or (f"g.whatsapp.net", 443)#{random.randint(1, 16)}
        self.proxy = proxy
        self.session_maker = session_maker
        self.device_config = device_config
        
        # Componentes principais
        self.connection: Optional[AsyncConnection] = None
        self.stream: Optional[AsyncSegmentedStream] = None
        self.bridge: Optional[TCPStreamBridge] = None
        self.handshake: Optional[AsyncWAHandshake] = None
        self.transport: Optional[AsyncWANoiseTransport] = None
        self.coder: Optional[AsyncCoder] = None
        self.axolotl_manager: Optional[AxolotlManager] = None
        
        # Stores e handlers (legacy - mantidos para compatibilidade)
        self.state_store: Optional[AsyncStateStore] = None
        self.message_handler: Optional[AsyncMessageHandler] = None
        self.acks_handler: Optional[AsyncAcksHandler] = None
        self.receipts_handler: Optional[AsyncReceiptHandler] = None
        self.presence_handler: Optional[AsyncPresenceHandler] = None
        self.auth_handler: Optional[AsyncAuthHandler] = None
        
        # Nova arquitetura de processors
        self._node_router: Optional[NodeRouter] = None
        self._encryption_receiver: Optional[EncryptionReceiver] = None
        self._encryption_sender: Optional[EncryptionSender] = None
        self._message_builder: Optional[MessageBuilder] = None
        self._iq_response_processor: Optional[IQResponseProcessor] = None
        
        # Handlers públicos
        self.group_handler: Optional[GroupHandler] = None
        self.contact_handler: Optional[ContactHandler] = None
        self.presence_handler_public: Optional[PresenceHandler] = None
        self.profile_handler: Optional[ProfileHandler] = None
        
        # Config
        self.profile: Optional[AsyncProfile] = None
        self.config: Optional[Config] = None
        self.bot_env: Optional[BotEnv] = None
        self.client_config: Optional[ClientConfig] = None
        self.network_config: NetworkConfig = NetworkConfig.direct()
        
        # Estado
        self._running = False
        self._connected = False
        self._authenticated = False
        
        # Prekeys não enviadas e retry
        self._unsent_prekeys: List = []
        self._pending_keys_retry: Optional[Tuple] = None
        self._keys_retry_lock = asyncio.Lock()
        
        # Fila de PKMSG pendentes (para evitar múltiplos pedidos simultâneos)
        # recipient_jid -> asyncio.Future (agrega múltiplos pedidos para o mesmo recipient)
        self._pending_keys_requests: Dict[str, asyncio.Future] = {}
        self._pending_keys_lock = asyncio.Lock()
        
        # Fila de PKMSG de sincronização em andamento (para evitar múltiplos envios simultâneos para o mesmo JID)
        # normalized_sender_jid -> asyncio.Future (para rastrear envio de PKMSG de sincronização)
        self._pending_pkmsg_sync_requests: Dict[str, asyncio.Future] = {}
        self._pending_pkmsg_sync_lock = asyncio.Lock()
        
        # Fila de mensagens enviadas (para retry)
        self._sent_messages_queue: List[ProtocolNode] = []
        self._MAX_SENT_QUEUE = 256
        
        # Mensagens pendentes (quando não há sessão)
        self._pending_messages: Dict[Tuple[str, Optional[str]], List[ProtocolNode]] = {}
        
        # Acompanhamento para validações e rate limiting
        self._last_sync_time: Dict[str, float] = {}  # Rastreia último sync por JID
        self._daily_message_count: int = 0  # Contador de mensagens diárias
        self._last_message_time: Dict[str, float] = {}  # Rastreia última mensagem por JID (rate limiting)
        
        # Tasks
        self._message_loop_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._bridge_task: Optional[asyncio.Task] = None
        
        # Eventos (opcional, para compatibilidade com API pública)
        self.events = AsyncEventEmitter()
    
    async def connect(self) -> None:
        """
        Conecta ao WhatsApp de forma totalmente linear e assíncrona.
        
        Fluxo completo:
        1. Inicializa componentes
        2. Conecta TCP socket
        3. Envia header WA\x06\x03
        4. Carrega/gera prekeys
        5. Cria stream
        6. Inicia bridge TCP ↔ Stream (ANTES do handshake)
        7. Executa handshake (linear, sem eventos)
        8. Aguarda <success> do servidor
        9. Inicia loops de processamento
        """
        try:
            logger.info(f"Conectando ao WhatsApp para {self.account_id}")
            
            # 1. Inicializa componentes
            await self._initialize_components()
            
            # 2. Gera prekeys ANTES da conexão para evitar timeout
            logger.info("Gerando prekeys antes da conexão...")
            prekeys_generated = await self._load_prekeys()
            logger.info("✓ Prekeys gerados")
            
            # 2.5. Verifica prekeys não enviadas e define passive=True se necessário
            # (Baseado em AxolotlControlLayer.on_connected() no zowsuplib)
            if self.axolotl_manager:
                try:
                    unsent_prekeys = await self.axolotl_manager.load_unsent_prekeys()
                    if unsent_prekeys is None:
                        unsent_prekeys = []
                    
                    if len(unsent_prekeys) > 0:
                        logger.info(f"Encontradas {len(unsent_prekeys)} prekeys não enviadas, definindo passive=True para handshake")
                        # Atualiza client_config com passive=True (será usado no handshake)
                        # CRÍTICO: O servidor precisa saber que este cliente precisa enviar prekeys
                        self.client_config = ClientConfig(
                            username=self.client_config.username,
                            passive=True,  # CRÍTICO: Define passive=True para o servidor saber que precisa enviar prekeys
                            pushname=self.client_config.pushname,
                            short_connect=self.client_config.short_connect,
                            useragent=self.client_config.useragent,
                        )
                        self._unsent_prekeys = unsent_prekeys[:]  # Armazena para envio após autenticação
                    else:
                        logger.debug("Nenhuma prekey não enviada encontrada, usando passive=False")
                        self._unsent_prekeys = []
                except Exception as e:
                    logger.warning(f"Erro ao verificar prekeys não enviadas (não crítico): {e}")
                    self._unsent_prekeys = []
            

            self.proxy = self.proxy or (await self.get_proxy())
            # 3. Conecta TCP socket
            if self.proxy:
                proxy_type = self.proxy.get("type", "http")
                proxy_host = self.proxy.get("host", "unknown")
                proxy_port = self.proxy.get("port", "unknown")
                logger.info(f" Conectando TCP socket via PROXY {proxy_type.upper()} ({proxy_host}:{proxy_port})...")
            else:
                logger.info("Conectando TCP socket (conexão direta, sem proxy)...")
            self.connection = AsyncConnection(self.endpoint, proxy=self.proxy)
            await self.connection.connect()
            if self.proxy:
                logger.info("✓ TCP socket conectado via PROXY")
            else:
                logger.info("✓ TCP socket conectado (direto)")
            
            # 4. Envia header WA\x06\x03
            logger.info("Enviando header WA\\x06\\x03...")
            await self.connection.send_header()
            logger.info("✓ Header enviado")
            
            # 5. Cria stream
            logger.info("Criando stream segmentado...")
            self.stream = AsyncSegmentedStream()
            logger.info("✓ Stream criado")
            
            # 6. Inicia bridge TCP ↔ Stream (CRÍTICO: ANTES do handshake)
            logger.info("Iniciando bridge TCP ↔ Stream (ANTES do handshake)...")
            self.bridge = TCPStreamBridge(self.connection, self.stream)
            self._bridge_task = asyncio.create_task(self.bridge.start())
            # Pequeno delay para garantir que bridge está rodando
            await asyncio.sleep(0.1)
            logger.info("✓ Bridge ativo")
            
            # 7. Executa handshake IMEDIATAMENTE após header (servidor espera atividade)
            logger.info("Executando handshake Noise...")
            await self._perform_handshake()
            logger.info("✓ Handshake concluído")
            
            # 7.5. Envia stream:stream após handshake (conforme fluxograma zowsuplib)
            # logger.info("Enviando stream:stream...")
            # await self._send_stream_start()
            # logger.info("✓ stream:stream enviado")
            
            # 8. Aguarda <success> do servidor (pode receber stream:features antes)
            logger.info("Aguardando confirmação do servidor (<success> ou stream:features)...")
            await self._wait_for_success()
            logger.info("✓ Autenticado com sucesso")
            
            # 8.5. Define PROP_IDENTITY_AUTOTRUST = True (conforme fluxograma zowsuplib)
            logger.info("Definindo PROP_IDENTITY_AUTOTRUST = True...")
            await self._set_identity_autotrust(True)
            logger.info("✓ PROP_IDENTITY_AUTOTRUST definido")
            
            # 8.6. Atualiza status da conta no banco de dados
            logger.info("Atualizando status da conta no banco...")
            await self._update_account_status()
            logger.info("✓ Status da conta atualizado")
            
            # 9. Inicializa handlers públicos (após conexão)
            logger.info("Inicializando handlers públicos...")
            await self._initialize_handlers()
            logger.info("✓ Handlers inicializados")
            
            # 9.5. Envia prekeys não enviadas (se houver)
            logger.info("Verificando prekeys não enviadas...")
            await self._check_and_flush_prekeys()
            logger.info("✓ Prekeys verificadas")
            
            # 10. Inicia loops de processamento
            logger.info("Iniciando loops de processamento...")
            self._running = True
            self._connected = True
            self._authenticated = True
            self._message_loop_task = asyncio.create_task(self._message_loop())
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            logger.info("✓ Cliente pronto")
            
            # Emite eventos para compatibilidade com API pública
            await self.events.emit("connected", {"account_id": self.account_id})
            await self.events.emit("authenticated", {"account_id": self.account_id})
            
            # Envia presence "available" após login (igual ao zowsuplib)
            # Baseado em yowbot_layer.onSuccess() linha 1025
            try:
                from .builders.presence_builder import PresenceBuilder
                presence_node = PresenceBuilder.build_presence(
                    presence_type=PresenceBuilder.TYPE_AVAILABLE
                )
                await self._send_protocol_node(presence_node)
                logger.debug("Presence 'available' enviado após login (igual ao zowsuplib)")
            except Exception as e:
                logger.warning(f"Erro ao enviar presence após login: {e}")
            
        except Exception as e:
            logger.error(f"Erro ao conectar: {e}", exc_info=True)
            # Emite evento de erro para compatibilidade com API pública
            await self.events.emit("connection:error", {"error": str(e)})
            await self.disconnect()
            raise
    
    async def _initialize_components(self) -> None:
        """Inicializa todos os componentes."""
        # Carrega proxy do banco de dados (se disponível)
        await self._load_proxy_from_db()
        
        # Profile
        self.profile = AsyncProfile(self.account_id, session_maker=self.session_maker)
        
        # State store
        self.state_store = AsyncStateStore(self.account_id, self.session_maker)
        
        # Axolotl manager
        factory = AxolotlManagerFactory(session_maker=self.session_maker)
        self.axolotl_manager = await factory.get_manager(self.account_id, self.account_id)
        
        # Coder (sem eventos - versão simplificada)
        # TODO: Criar AsyncCoder sem eventos se necessário
        from ..core.events import AsyncEventEmitter
        events = AsyncEventEmitter()
        self.coder = AsyncCoder(events)
        
        # Handlers (legacy - mantidos para compatibilidade)
        # Configura send_ack_fn para o message_handler enviar acks de delivery
        
        self.message_handler = AsyncMessageHandler(events)
        self.acks_handler = AsyncAcksHandler(events)
        self.receipts_handler = AsyncReceiptHandler(events)
        self.presence_handler = AsyncPresenceHandler(events)
        self.auth_handler = AsyncAuthHandler(events)
        
        # Nova arquitetura de processors
        self._node_router = NodeRouter()
        
        # IQ Response Processor
        self._iq_response_processor = IQResponseProcessor()
        
        # Encryption layer
        self._encryption_receiver = EncryptionReceiver(
            self.axolotl_manager,
            get_keys_fn=None,  # Será configurado após conexão
            process_pending_fn=None  # Será configurado após conexão
        )
        self._encryption_sender = EncryptionSender(self.axolotl_manager)
        
        # Message builder
        self._message_builder = MessageBuilder(self._encryption_sender)
        
        # Media components (para envio de mídia)
        from .media.media_cipher import MediaCipher
        from .media.media_uploader import AsyncMediaUploader
        from .media.media_connection import MediaConnection
        
        self._media_cipher = MediaCipher()
        self._media_uploader = AsyncMediaUploader()
        self._media_connection = MediaConnection()
        
        # Configura função para obter media connection via IQ
        async def get_media_conn_fn():
            """
            Obtém media connection via IQ media_conn.
            
            Returns:
                MediaConnectionInfo ou None se falhar
            """
            from .media.media_connection import MediaConnectionInfo
            
            # Cria IQ request para media_conn
            iq_id = ProtocolNode._generateId()
            query_node = ProtocolNode(tag="media_conn")
            iq_node = ProtocolNode(
                tag="iq",
                attributes={
                    "id": iq_id,
                    "type": "set",
                    "xmlns": "w:m",
                    "to": "s.whatsapp.net"
                },
                children=[query_node]
            )
            
            # Event para aguardar resposta
            response_event = asyncio.Event()
            response_data = {"info": None, "error": None}
            
            # Registra callback para processar resposta
            async def handle_response(node: ProtocolNode):
                try:
                    # Verifica se é resposta válida
                    if node.get_attribute("type") == "error":
                        error_node = node.get_child("error")
                        error_msg = error_node.get_attribute("text") if error_node else "Unknown error"
                        logger.error(f"Erro ao obter media connection: {error_msg}")
                        response_data["error"] = RuntimeError(f"Erro ao obter media connection: {error_msg}")
                        response_event.set()
                        return
                    
                    # Extrai media_conn do node
                    media_conn_node = node.get_child("media_conn")
                    if not media_conn_node:
                        logger.error("Resposta de media_conn sem node media_conn")
                        response_data["error"] = RuntimeError("Resposta inválida: sem node media_conn")
                        response_event.set()
                        return
                    
                    # Extrai hosts
                    # Baseado em ResultRequestMediaConnIqProtocolEntity.fromProtocolTreeNode() do zowsuplib
                    # Os nodes são <host> com atributo hostname (não <hostname>)
                    hosts = []
                    host_nodes = media_conn_node.get_all_children("host")
                    if host_nodes:
                        for host_node in host_nodes:
                            # Extrai hostname do atributo do node <host>
                            hostname = host_node.get_attribute("hostname")
                            if hostname:
                                hosts.append(hostname)
                    else:
                        # Fallback: tenta obter do atributo hostname do próprio node (formato antigo)
                        hostname = media_conn_node.get_attribute("hostname")
                        if hostname:
                            hosts.append(hostname)
                    
                    # Extrai auth
                    auth = media_conn_node.get_attribute("auth") or ""
                    
                    # Extrai TTL (padrão 86400 segundos = 24h)
                    ttl_str = media_conn_node.get_attribute("ttl") or "86400"
                    try:
                        ttl = int(ttl_str)
                    except ValueError:
                        logger.warning(f"TTL inválido '{ttl_str}', usando padrão 86400")
                        ttl = 86400
                    
                    if not hosts:
                        logger.error("Resposta de media_conn sem hosts")
                        response_data["error"] = RuntimeError("Resposta inválida: sem hosts")
                        response_event.set()
                        return
                    
                    # Cria MediaConnectionInfo
                    connection_info = MediaConnectionInfo(
                        hosts=hosts,
                        auth=auth,
                        ttl=ttl,
                        timestamp=time.time()
                    )
                    
                    response_data["info"] = connection_info
                    response_event.set()
                    
                except Exception as e:
                    logger.error(f"Erro ao processar resposta de media_conn: {e}", exc_info=True)
                    response_data["error"] = e
                    response_event.set()
            
            # Registra callback
            self._iq_response_processor.register_callback(iq_id, handle_response, timeout=30.0)
            
            try:
                # Envia IQ request
                await self._send_protocol_node(iq_node)
                logger.debug(f"IQ request para media_conn enviado (id={iq_id})")
                
                # Aguarda resposta (timeout de 30 segundos)
                try:
                    await asyncio.wait_for(response_event.wait(), timeout=30.0)
                except asyncio.TimeoutError:
                    self._iq_response_processor.unregister_callback(iq_id)
                    logger.error("Timeout ao aguardar resposta de media_conn")
                    return None
                
                # Verifica se houve erro
                if response_data["error"]:
                    raise response_data["error"]
                
                # Retorna connection info
                return response_data["info"]
                
            except Exception as e:
                logger.error(f"Erro ao obter media connection: {e}", exc_info=True)
                self._iq_response_processor.unregister_callback(iq_id)
                return None
        
        self._media_connection.set_get_media_conn_fn(get_media_conn_fn)
        
        # Message parser
        message_parser = AsyncMessageParser()
        
        # ReceiptBuilder
        from .builders.receipt_builder import ReceiptBuilder
        receipt_builder = ReceiptBuilder()
        
        # Função para enviar receipt
        async def send_receipt_fn(receipt_node: ProtocolNode):
            await self._send_protocol_node(receipt_node)
        
        # Registra processors
        self._node_router.register(
            MessageProcessor(
                encryption_receiver=self._encryption_receiver,
                message_parser=message_parser,
                events=self.events,
                receipt_builder=receipt_builder,
                send_receipt_fn=send_receipt_fn
            )
        )
        # ReceiptProcessor precisa de funções do client
        # Conecta funções do client ao ReceiptProcessor
        async def get_enqueued_message_wrapper(message_id: str, keep_enqueued: bool = False):
            return await self._get_enqueued_message(message_id, keep_enqueued)
        
        async def resend_message_wrapper(message_node: ProtocolNode, retry_jid: Optional[str] = None, retry_count: int = 0):
            return await self._resend_message_for_retry(message_node, retry_jid, retry_count)
        
        receipt_processor = ReceiptProcessor(
            events=self.events,
            get_enqueued_message_fn=get_enqueued_message_wrapper,
            resend_message_fn=resend_message_wrapper
        )
        self._node_router.register(receipt_processor)
        self._receipt_processor = receipt_processor  # Guarda referência
        
        # Handler para enviar ACKs de retry
        async def handle_ack_send(data: dict):
            ack_node = data.get("node")
            if ack_node:
                await self._send_protocol_node(ack_node)
        
        self.events.on("ack:send", handle_ack_send)
        
        async def handle_stream_error(_data: dict) -> None:
            if not self._running:
                return
            logger.warning("stream:error recebido; desconectando conta")
            asyncio.create_task(self.disconnect())

        self.events.on("stream:error", handle_stream_error)

        self._node_router.register(StreamErrorProcessor(self.events))
        self._node_router.register(AckProcessor(self.events))
        self._node_router.register(PresenceProcessor(self.events))
        # IQProcessor precisa do IQResponseProcessor para chamar callbacks
        # CORREÇÃO: Passa função de envio para IQProcessor responder pong quando recebe ping
        async def send_node_fn(node: ProtocolNode):
            await self._send_protocol_node(node)
        
        self._node_router.register(IQProcessor(
            self.events, 
            self._iq_response_processor,
            send_node_fn=send_node_fn
        ))
        
        # NotificationProcessor precisa de funções do client
        # Será configurado após conexão quando _send_ack estiver disponível
        notification_processor = NotificationProcessor(
            events=self.events,
            flush_prekeys_fn=self._check_and_flush_prekeys,  # Será configurado após conexão
            get_keys_fn=None,  # Será configurado após conexão
            send_ack_fn=None  # Será configurado após conexão
        )
        self._node_router.register(notification_processor)
        self._notification_processor = notification_processor  # Guarda referência para atualizar depois
        
        self._node_router.register(GroupProcessor(self.events))
        
        # Inicializa handlers públicos (serão configurados após conexão)
        # Os handlers precisam de send_iq_fn e send_presence_fn que só existem após conexão
        # Será chamado em _initialize_handlers() após conexão
        
        # Client config (para handshake)
        from ..config.network import NetworkEnv
        from ..noise.config import UserAgentConfig, AppVersionConfig
        from ..utils.phone import PhoneUtils
        
        env_name = "smb_android"
        if self.device_config:
            if isinstance(self.device_config, str):
                env_name = self.device_config
            elif hasattr(self.device_config, 'name'):
                env_name = self.device_config.name
        
        logger.debug(f"env_name: {env_name}")
        
        # Cria ambiente de dispositivo
        from ..config.device_env import DeviceEnv
        device_env = DeviceEnv(env_name, random=False)
        
        # Cria ambiente de rede
        network_env = NetworkEnv(NetworkEnv.TYPE_DIRECT)
        
        # Cria BotEnv
        self.bot_env = BotEnv(device_env, network_env)
        
        # Obtém MCC/MNC do número
        mcc, mnc = PhoneUtils.get_mcc_mnc(self.account_id)
        
        # Obtém platform ID
        platform_id = self.bot_env.deviceEnv.getPlatform()
        
        # Carrega config
        self.config = await self.profile.config
        
        # Gera fdid/expid se necessário
        if self.config.fdid is None:
            self.config.fdid = WATools.generatePhoneId(self.bot_env.deviceEnv)
            self.config.expid = WATools.generateDeviceId()
            await self.profile.write_config(self.config)
        
        # Atualiza device info se necessário
        if self.config.device_name is not None:
            self.bot_env.deviceEnv.setOSName(self.config.os_name)
            self.bot_env.deviceEnv.setOSVersion(self.config.os_version)
            self.bot_env.deviceEnv.setManufacturer(self.config.manufacturer)
            self.bot_env.deviceEnv.setDeviceName(self.config.device_name)
            self.bot_env.deviceEnv.setDeviceModelType(self.config.device_model_type)
        else:
            self.config.os_name = self.bot_env.deviceEnv.getOSName()
            self.config.os_version = self.bot_env.deviceEnv.getOSVersion()
            self.config.manufacturer = self.bot_env.deviceEnv.getManufacturer()
            self.config.device_name = self.bot_env.deviceEnv.getDeviceName2()
            self.config.device_model_type = self.bot_env.deviceEnv.getDeviceModelType()
            await self.profile.write_config(self.config)
        
        cc = PhoneUtils.getMobileCC(self.account_id)
        lg, lc = PhoneUtils.getLGLC(cc)
        
        # Cria user agent
        useragent = UserAgentConfig(
            platform=platform_id,
            app_version=AppVersionConfig(self.bot_env.deviceEnv.getVersion()),
            mcc=mcc or "724",
            mnc=mnc or "05",
            os_version=self.bot_env.deviceEnv.getOSVersion(),
            manufacturer=self.bot_env.deviceEnv.getManufacturer(),
            device=self.bot_env.deviceEnv.getDeviceName(),
            os_build_number=self.bot_env.deviceEnv.getBuildVersion(),
            phone_id=self.config.fdid,
            locale_lang=lg,
            locale_country=lc,
            device_exp_id=base64.b64encode(self.config.expid).decode() if self.config.expid else "",
            device_type=0,
            device_model_type=self.bot_env.deviceEnv.getDeviceModelType(),
        )
        
        # Obtém username
        username = await self.profile.username if self.profile else None
        if not username:
            username = self.account_id.replace("+", "").replace("-", "").replace(" ", "")
        
        # Cria client config
        self.client_config = ClientConfig(
            username=int(username),
            passive=False,
            pushname="ZowPy",
            short_connect=True,
            useragent=useragent,
        )

        logger.info(f"client_config: {self.client_config}")
    
    async def _load_prekeys(self) -> None:
        """Carrega/gera prekeys (equivalente a AxolotlControlLayer.level_prekeys())."""
        if not self.axolotl_manager:
            logger.warning("AxolotlManager não disponível, pulando geração de prekeys")
            return
        
        try:
            prekeys = await self.axolotl_manager.level_prekeys()
            if prekeys:
                logger.info(f"Geradas {len(prekeys)} prekeys com sucesso")
            else:
                logger.info("Prekeys já existem em quantidade suficiente")

            return prekeys
        except Exception as e:
            logger.warning(f"Erro ao gerar prekeys (não crítico): {e}")

            return []

    
    async def _perform_handshake(self) -> None:
        """
        Executa handshake de forma totalmente linear, sem eventos.
        
        Baseado no zowsuplib:
        - Carrega local_static e remote_static
        - Executa handshake IK (se RS existe) ou XX (se não existe)
        - Cria transport após handshake
        """
        import base64
        from dissononce.dh.x25519.public import PublicKey as DissononcePublicKey
        
        logger.info("Iniciando handshake Noise")
        
        # Verifica se profile existe
        if not self.profile:
            raise RuntimeError("Profile não encontrado - use import_account_from_six_parts para importar a conta primeiro")
        
        # Carrega local static keypair
        local_static = self.config.client_static_keypair
        if not local_static:
            raise RuntimeError("client_static_keypair não encontrado")
        
        if isinstance(local_static, bytes):
            local_static = KeyPair.from_bytes(local_static)
        
        logger.debug(f"local_static carregado: {type(local_static)}")
        
        # Carrega remote static (se disponível)
        remote_static = self.config.server_static_public
        logger.debug(f"remote_static: {'presente' if remote_static else 'não presente'}")
        
        # Cria handshake
        handshake = AsyncWAHandshake(version_major=6, version_minor=3)
        
        # Executa handshake (linear, bloqueia até concluir)
        logger.info("Executando handshake.perform()...")
        cipher_states = await handshake.perform(
            client_config=self.client_config,
            stream=self.stream,
            s=local_static,
            rs=remote_static
        )
        
        if not cipher_states:
            raise HandshakeFailedException("Handshake retornou None (sem cipher states)")
        
        logger.info("Handshake concluído, criando transport...")
        
        # Cria transport
        self.transport = AsyncWANoiseTransport(
            stream=self.stream,
            send_cipherstate=cipher_states[0],
            recv_cipherstate=cipher_states[1]
        )
        
        # Salva remote static se foi recebida durante handshake
        if handshake.rs:
            logger.info("Salvando chave RS remota recebida durante handshake...")
            self.config.server_static_public = handshake.rs
            await self.profile.write_config(self.config)
            logger.info("✓ Chave RS remota salva")
        
        logger.info("✓ Transport criado")
    
    async def _send_stream_start(self) -> None:
        """
        Envia stream:stream para o servidor após handshake.
        
        Baseado no fluxograma do zowsuplib:
        - Após ProtocolReady, envia stream:stream para iniciar o stream XMPP
        """
        logger.info("Enviando stream:stream para o servidor...")
        
        stream_node = ProtocolNode(
            tag="stream:stream",
            attributes={
                "to": "s.whatsapp.net",
                "version": "1.0",
                "xmlns": "jabber:client",
                "xmlns:stream": "http://etherx.jabber.org/streams"
            }
        )
        
        await self._send_protocol_node(stream_node)
        logger.info("✓ stream:stream enviado")
    
    async def _send_auth_credentials(self) -> None:
        """
        Envia credenciais de autenticação após receber stream:features.
        
        Baseado no fluxograma do zowsuplib:
        - Após receber stream:features, envia <auth> com credenciais
        - Inclui o atributo 'passive' conforme client_config.passive (igual ao zowsuplib)
        """
        logger.info("Enviando <auth> com credenciais...")
        
        # Obtém username do profile
        username = await self.profile.username if self.profile else None
        if not username:
            username = self.account_id.replace("+", "").replace("-", "").replace(" ", "")
        
        # Obtém valor de passive do client_config (padrão False)
        passive = getattr(self.client_config, 'passive', False) if self.client_config else False
        
        # Cria node <auth> conforme protocolo WhatsApp
        # CRÍTICO: Incluir 'passive' como no zowsuplib (AuthProtocolEntity.toProtocolTreeNode)
        auth_node = ProtocolNode(
            tag="auth",
            attributes={
                "mechanism": "WAUTH-2",
                "user": str(username),
                "passive": "true" if passive else "false",  # Conforme zowsuplib
            }
        )
        
        await self._send_protocol_node(auth_node)
        logger.info(f"✓ <auth> enviado com user={username}, passive={passive}")
    
    async def _set_identity_autotrust(self, value: bool) -> None:
        """
        Define PROP_IDENTITY_AUTOTRUST.
        
        Baseado no fluxograma do zowsuplib:
        - Após login bem-sucedido, define PROP_IDENTITY_AUTOTRUST = True
        - Isso permite confiar automaticamente em identidades recebidas
        
        No zowpy, isso é usado pelo axolotl_manager ao criar sessões.
        O valor é armazenado como atributo do cliente para uso futuro.
        """
        # Armazena como atributo do cliente
        self._identity_autotrust = value
        
        # O axolotl_manager já usa autotrust=True ao criar sessões
        # Este flag pode ser usado para outras operações que precisem confiar automaticamente
        logger.info(f"PROP_IDENTITY_AUTOTRUST definido como {value}")
        
        # Log para debug
        if self.axolotl_manager:
            logger.debug(f"identity_autotrust={value} será usado pelo axolotl_manager ao criar sessões")
    
    async def _update_account_status(self) -> None:
        """
        Atualiza status da conta no banco de dados após autenticação.
        
        Baseado no fluxograma do zowsuplib:
        - update_account_status: marca conta como logged_in
        """
        if not self.session_maker:
            logger.debug("db_pool não disponível, pulando atualização de status")
            return
        
        try:
            from ..db.models import Account
            from sqlalchemy import select
            
            async with self.session_maker() as session:
                result = await session.execute(
                    select(Account).filter_by(phone=self.account_id)
                )
                account = result.scalar_one_or_none()
                
                if account:
                    account.is_logged_in = True
                    account.is_initialized = True
                    
                    # Atualiza pushname se disponível no config
                    if self.config and self.config.pushname:
                        account.pushname = self.config.pushname
                    
                    await session.commit()
                    logger.info(f"Account {self.account_id} marcado como logged_in no banco")
                else:
                    logger.warning(f"Account {self.account_id} não encontrado no banco para atualizar status")
        except Exception as e:
            logger.warning(f"Erro ao atualizar status de login no banco: {e}", exc_info=True)
    
    async def _wait_for_success(self, timeout: float = 30.0) -> None:
        """
        Aguarda <success> do servidor de forma linear.
        
        Baseado no zowsuplib:
        - Após enviar stream:stream, servidor pode enviar stream:features
        - Se receber stream:features, envia <auth> com credenciais
        - Servidor então envia <success> ou <failure>
        
        Args:
            timeout: Timeout em segundos
        
        Raises:
            AuthenticationError: Se receber <failure> ou timeout
        """
        logger.info("Aguardando <success> do servidor...")
        
        start_time = time.time()
        
        while True:
            # Verifica timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise AuthenticationError(f"Timeout aguardando <success> após {timeout}s")
            
            # Recebe mensagem descriptografada
            try:
                remaining_timeout = timeout - elapsed
                decrypted = await self.transport.recv(timeout=remaining_timeout)
            except asyncio.TimeoutError:
                logger.debug("Timeout aguardando mensagem do servidor, continuando...")
                continue
            except Exception as e:
                logger.error(f"Erro ao receber mensagem: {e}")
                raise AuthenticationError(f"Erro ao receber mensagem: {e}")
            
            if not decrypted:
                continue
            
            # Decodifica protocol node
            try:
                node = await self.coder.receive_and_decode(decrypted)
            except Exception as e:
                logger.warning(f"Erro ao decodificar node: {e}, ignorando...")
                continue
            
            if not node:
                continue

            logger.debug(f"Node recebido: {node}")
            logger.info(f"Node recebido: tag={node.tag}")
             
            # Processa node
            if node.tag == "success":
                logger.info("✓ <success> recebido do servidor")
                return  # Sucesso!
            elif node.tag == "failure":
                error_code = node.get_attribute("code") or node.get_attribute("reason") or "unknown"
                logger.error(f"<failure> recebido: code={error_code}")
                raise AuthenticationError(f"Login falhou: code={error_code}")
            elif node.tag == "stream:features":
                logger.info("stream:features recebido, enviando <auth>...")
                # Processa stream:features e envia auth
                await self.auth_handler.handle_stream_features(node)
                # Envia <auth> após receber stream:features
                await self._send_auth_credentials()
                logger.info("✓ <auth> enviado após stream:features")
                continue
            else:
                logger.debug(f"Node {node.tag} recebido antes de autenticação, ignorando...")
                continue
    
    async def _message_loop(self) -> None:
        """
        Loop de processamento de mensagens com processamento paralelo.
        
        Separa recepção de nodes do processamento, permitindo que múltiplos nodes
        sejam processados simultaneamente sem que um bloqueie o outro.
        """
        logger.info("Message loop iniciado (com processamento paralelo)")
        
        # Fila assíncrona para nodes recebidos
        # maxsize=100 para evitar acúmulo excessivo (nodes serão descartados se fila cheia)
        node_queue = asyncio.Queue(maxsize=100)
        
        # Número de workers para processar nodes em paralelo
        # 3 workers permite processar até 3 nodes simultaneamente
        num_workers = 3
        
        # Task para receber nodes (não bloqueia processamento)
        async def receive_loop():
            """Loop dedicado apenas para receber nodes e colocá-los na fila."""
            logger.debug("Receive loop iniciado")
            
            while self._running:
                try:
                    if not self.transport:
                        await asyncio.sleep(0.5)
                        continue
                    
                    # Recebe mensagem descriptografada
                    decrypted = await self.transport.recv(timeout=1.0)
                    if not decrypted:
                        continue
                    
                    # Decodifica protocol node
                    node = await self.coder.receive_and_decode(decrypted)
                    if not node:
                        continue
                    
                    logger.debug(f"Node recebido: {node}")
                    
                    # Coloca node na fila para processamento (não bloqueia recepção)
                    try:
                        logger.debug(f"Worker ANTES de processar node {node.tag}")
                        await asyncio.wait_for(node_queue.put((node, decrypted)), timeout=0.1)
                        logger.debug(f"Worker DEPOIS de processar node {node.tag}")
                        logger.debug(f"Node {node.tag} enfileirado (queue_size={node_queue.qsize()})")
                    except asyncio.TimeoutError:
                        logger.warning(f"Fila de nodes cheia (qsize={node_queue.qsize()}), descartando node {node.tag} (pode indicar processamento lento)")
                        continue
                        
                except asyncio.TimeoutError:
                    continue
                except StreamCancelledError:
                    logger.info("Stream cancelado, encerrando receive loop")
                    break
                except Exception as e:
                    logger.error(f"Erro no receive loop: {e}", exc_info=True)
                    await asyncio.sleep(0.1)
                    continue
            
            logger.debug("Receive loop encerrado")
        
        # Worker para processar nodes da fila
        async def process_worker(worker_id: int):
            """Worker que processa nodes da fila em paralelo."""
            logger.debug(f"Worker {worker_id} iniciado")
            
            while self._running:
                try:
                    # Aguarda node da fila (com timeout para verificar _running periodicamente)
                    try:
                        node, raw_data = await asyncio.wait_for(node_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    
                    logger.debug(f"Worker {worker_id} processando node {node.tag} (queue_size={node_queue.qsize()})")
                    
                    # Processa node (pode demorar ou falhar, mas não bloqueia outros workers)
                    try:
                        logger.debug(f"Worker {worker_id} ANTES de processar node {node.tag}")
                        await self._process_protocol_node(node, raw_data=raw_data)
                        logger.debug(f"Worker {worker_id} DEPOIS de processar node {node.tag}")
                    except Exception as e:
                        logger.error(f"Erro ao processar node {node.tag} no worker {worker_id}: {e}", exc_info=True)
                    finally:
                        # Marca task como concluída
                        node_queue.task_done()
                        logger.debug(f"Worker {worker_id} concluiu processamento de node {node.tag}")
                        
                except Exception as e:
                    logger.error(f"Erro no worker {worker_id}: {e}", exc_info=True)
                    await asyncio.sleep(0.1)
                    continue
            
            logger.debug(f"Worker {worker_id} encerrado")
        
        # Inicia receive loop e workers
        receive_task = asyncio.create_task(receive_loop())
        worker_tasks = [asyncio.create_task(process_worker(i)) for i in range(num_workers)]
        
        try:
            # Aguarda todas as tasks
            await asyncio.gather(receive_task, *worker_tasks)
        except Exception as e:
            logger.error(f"Erro no message loop: {e}", exc_info=True)
        finally:
            # Cancela tasks ao encerrar
            receive_task.cancel()
            for task in worker_tasks:
                task.cancel()
            
            # Aguarda cancelamento
            await asyncio.gather(receive_task, *worker_tasks, return_exceptions=True)
            logger.info("Message loop encerrado")
    
    async def _process_protocol_node(self, node: ProtocolNode, raw_data: Optional[bytes] = None) -> None:
        """
        Processa node do protocolo usando NodeRouter.
        
        Usa a nova arquitetura de processors para processar nodes de forma moderna e limpa.
        """
        try:
            # Usa router para processar node
            result = await self._node_router.route(node, raw_data)
            
            if result is None:
                logger.debug(f"Node {node.tag} não processado por nenhum processor")
        
        except Exception as e:
            logger.error(f"Erro ao processar node {node.tag}: {e}", exc_info=True)
    
    async def _initialize_handlers(self) -> None:
        """Inicializa handlers públicos após conexão."""
        # Função para enviar IQ
        async def send_iq_fn(iq_node: ProtocolNode):
            await self._send_protocol_node(iq_node)
        
        # Função para enviar presence
        async def send_presence_fn(presence_node: ProtocolNode):
            await self._send_protocol_node(presence_node)
        
        # Inicializa handlers
        self.group_handler = GroupHandler(
            send_iq_fn=send_iq_fn,
            iq_response_processor=self._iq_response_processor
        )
        
        self.contact_handler = ContactHandler(
            send_iq_fn=send_iq_fn,
            iq_response_processor=self._iq_response_processor
        )
        
        self.presence_handler_public = PresenceHandler(
            send_presence_fn=send_presence_fn
        )
        
        self.profile_handler = ProfileHandler(
            send_iq_fn=send_iq_fn,
            iq_response_processor=self._iq_response_processor
        )
        
        self.integrity_handler = IntegrityHandler(
            send_iq_fn=send_iq_fn,
            iq_response_processor=self._iq_response_processor
        )
        
        # Atualiza EncryptionReceiver com funções disponíveis
        if self._encryption_receiver:
            self._encryption_receiver._get_keys = self._get_keys_for_recipient
            self._encryption_receiver._process_pending = self._process_pending_messages
            self._encryption_receiver._send_pkmsg_for_invalid_message = self._send_pkmsg_for_invalid_message
            self._encryption_receiver._send_retry_receipt_fn = self._send_retry_receipt
            self._encryption_receiver._send_receipt_on_error_fn = self._send_receipt_on_error
            self._encryption_receiver._get_registration_id_fn = self._get_registration_id
    
    async def _handle_iq(self, node: ProtocolNode) -> None:
        """Processa IQ recebido."""
        iq_type = node.get_attribute("type")
        iq_id = node.get_attribute("id")
        iq_from = node.get_attribute("from")
        logger.info(f"[IQ] IQ recebido no client._handle_iq: type={iq_type}, id={iq_id}, from={iq_from}")
        logger.debug(f"Processando IQ: {node.get_attribute('type')}")
        # Processa resposta de IQ através do IQResponseProcessor
        if self._iq_response_processor:
            processed = await self._iq_response_processor.process_iq_response(node)
            # Se não foi processado e é erro, tenta processar erro de prekeys
            if not processed and node.get_attribute("type") == "error":
                iq_id = node.get_attribute("id")
                # Verifica se é erro de prekeys (pode ter callback de erro registrado)
                # Por enquanto, apenas loga
                logger.debug(f"IQ error não processado: {iq_id}")
    
    async def _keepalive_loop(self) -> None:
        """Loop de keepalive."""
        while self._running:
            try:
                await asyncio.sleep(20)
                if self._connected and self._authenticated:
                    await self._send_keepalive()
            except Exception as e:
                logger.error(f"Erro no keepalive: {e}")
    
    async def _send_keepalive(self) -> None:
        """Envia keepalive."""
        keepalive_node = ProtocolNode(
            tag="iq",
            attributes={
                "id":ProtocolNode._generateId(),
                "type": "get",
                "xmlns": "w:p",
            }
        )
        await self._send_protocol_node(keepalive_node)
    
    async def _send_ack(
        self,
        message_id: str,
        message_type: str,
        notification_type: str,
        from_jid: str
    ) -> None:
        """
        Envia ACK para notification ou message.
        
        Baseado em OutgoingAckProtocolEntity.
        
        Args:
            message_id: ID da mensagem/notification
            message_type: Tipo da mensagem (notification, message, etc.)
            notification_type: Tipo da notification (encrypt, etc.)
            from_jid: JID do remetente
        """
        ack_node = ProtocolNode(
            tag="ack",
            attributes={
                "id": message_id,
                "class": message_type,
                "type": notification_type,
                "to": from_jid
            },
            children=[]
        )
        await self._send_protocol_node(ack_node)
        logger.debug(f"ACK enviado: id={message_id}, type={notification_type}, to={from_jid}")
    
    async def _send_protocol_node(self, node: ProtocolNode) -> None:
        """
        Envia protocol node.
        
        Valida estrutura antes de enviar e loga detalhes.
        """

        logger.debug(f"Enviando node: {node}")

        if not self.transport:
            raise RuntimeError("Transport não disponível")
        
        # Validação da estrutura (para debug)
        if logger._core.min_level <= 10:  # DEBUG
            self._validate_node_structure(node)
        
        # Codifica node
        encoded_bytes = await self.coder.encoder.encode(node)

        # logger.debug(f"Encoded bytes: {encoded_bytes}")
        
        # Converte lista para bytes se necessário (WriteEncoder retorna lista)
        if isinstance(encoded_bytes, list):
            encoded_bytes = bytes(encoded_bytes)
        
        logger.debug(f"Enviando node {node.tag}: {len(encoded_bytes)} bytes")
        
        # Envia via transport (criptografa e envia)
        await self.transport.send(encoded_bytes)
    
    def _validate_node_structure(self, node: ProtocolNode) -> None:
        """
        Valida estrutura do node antes de enviar (apenas para debug).
        
        Verifica:
        - Se enc entities estão corretas
        - Se participants node está correto (se grupo)
        - Se elementos extras estão presentes
        """
        if node.tag != "message":
            return
        
        # Verifica enc entities
        enc_nodes = [c for c in node.children if c.tag == "enc"]
        participants_node = node.get_child("participants")
        
        logger.debug(f"Node structure validation:")
        logger.debug(f"  - Tag: {node.tag}")
        logger.debug(f"  - Enc nodes: {len(enc_nodes)}")
        logger.debug(f"  - Participants node: {participants_node is not None}")
        
        if participants_node:
            to_nodes = [c for c in participants_node.children if c.tag == "to"]
            logger.debug(f"  - To nodes in participants: {len(to_nodes)}")
        
        # Verifica elementos extras
        reporting = node.get_child("reporting")
        device_identity = node.get_child("device-identity")
        tctoken = node.get_child("tctoken")
        biz = node.get_child("biz")
        
        logger.debug(f"  - Reporting: {reporting is not None}")
        logger.debug(f"  - Device-identity: {device_identity is not None}")
        logger.debug(f"  - Tctoken: {tctoken is not None}")
        logger.debug(f"  - Biz: {biz is not None}")
    
    async def assure_contacts_and_send(
        self,
        to: str,
        text: str,
        message_id: Optional[str] = None
    ) -> str:
        """
        Garante que contato está sincronizado antes de enviar mensagem.
        
        Equivalente ao assureContactsAndSend() do zowsuplib.
        Implementa estratégia anti-banimento com validações robustas.
        
        Args:
            to: JID do destinatário
            text: Texto da mensagem
            message_id: ID da mensagem (gerado se None)
        
        Returns:
            ID da mensagem enviada
        
        Raises:
            RuntimeError: Se conta está restrita ou limite diário atingido
            ValueError: Se JID é inválido ou número está na lista de inválidos
        """
        
        # 3. Normaliza JID
        from ..utils.jid import normalize
        normalized_jid = normalize(to)
        if not normalized_jid:
            logger.error(f"assure_contacts_and_send: falha ao normalizar JID: {to}")
            raise ValueError(f"JID inválido: {to}")
        
        phone = normalized_jid.split('@')[0] if '@' in normalized_jid else normalized_jid

        # 5. Verifica se contato é novo
        if not self.axolotl_manager:
            raise ValueError

        is_new_contact = await self.axolotl_manager._store.isNewContact(normalized_jid)
        
        if is_new_contact:
            logger.info(f"Contato {normalized_jid} é novo, sincronizando e validando antes de enviar...")
            
            await self.axolotl_manager._store.addContact(normalized_jid)
            
            # 8. Sincroniza contato
            if self.contact_handler:
                try:
                    result = await self.contact_handler.sync_contacts([phone], mode="delta", context="interactive")
                    logger.info(f"Contato {normalized_jid} sincronizado com sucesso")
                    
                    return await self._send_text_direct(to, text, message_id)
                except Exception as e:
                    logger.error(f"Erro ao sincronizar contato {normalized_jid}: {e}")
                    # Remove contato se sincronização falhou
                    try:
                        await self.axolotl_manager._store.removeContact(normalized_jid)
                    except Exception:
                        pass
                    raise
            else:
                logger.warning("ContactHandler não disponível, enviando sem sincronizar")
                # Atualiza timestamp mesmo sem sincronizar
                self._last_sync_time[normalized_jid] = time.time()
                await self._check_rate_limit(normalized_jid, min_delay_seconds=2.0)
                return await self._send_text_direct(to, text, message_id)
        else:
            logger.debug(f"Contato {normalized_jid} já existe nos contatos")
            # Aplica rate limiting mesmo para contatos conhecidos
            await self._check_rate_limit(normalized_jid, min_delay_seconds=2.0)
            return await self._send_text_direct(to, text, message_id)

    
    async def _send_text_direct(
        self,
        to: str,
        text: str,
        message_id: Optional[str] = None
    ) -> str:
        """
        Envia mensagem de texto diretamente (sem validações de contato).
        
        Este método é chamado por assure_contacts_and_send() após validações.
        
        Args:
            to: JID do destinatário
            text: Texto da mensagem
            message_id: ID da mensagem (gerado se None)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        is_group = to.endswith(f"@{YowConstants.WHATSAPP_GROUP_SERVER}")
        to_jid = to_whatsapp_jid(to, is_group)
        
        # Incrementa contador de mensagens diárias
        self._daily_message_count += 1
        
        # 1. Gera ID se não fornecido
        if not message_id:
            message_id = ProtocolNode._generateId()
            logger.debug(f"Generated message ID: {message_id}")
        
        # 2. Cria ExtendedTextMessageProtocolEntity
        from ..protocol.entities import ExtendedTextMessageProtocolEntity
        from ..proto.e2e_pb2 import Message as MessagePb
        
        # Cria entidade de mensagem estendida
        message_entity = ExtendedTextMessageProtocolEntity(
            to=to_jid,
            text=text,
            message_id=message_id
        )
        
        # 3. Gera protobuf usando o método to_protobuf() da entidade
        # Cria Message protobuf completo
        message_pb = MessagePb()
        
        # Adiciona ExtendedTextMessage ao protobuf
        ext_text = message_entity.to_protobuf()
        message_pb.extended_text_message.CopyFrom(ext_text)
        
        # Serializa protobuf
        proto_bytes = message_pb.SerializeToString()
        logger.debug(f"Protobuf serializado: {len(proto_bytes)} bytes")
        
        # 4. Adiciona node <proto> à entidade (ExtendedTextMessageProtocolEntity cria automaticamente se proto_data for fornecido)
        # Mas como já criamos a entidade, adicionamos manualmente
        from ..protocol.entities import ProtocolEntity
        proto_node = ProtocolEntity(
            tag="proto",
            attributes={"mediatype": "text"},
            data=proto_bytes
        )
        message_entity.children.append(proto_node)
        
        # 5. Usa a entidade diretamente (herda de ProtocolNode)
        # ExtendedTextMessageProtocolEntity herda de ProtocolEntity que herda de ProtocolNode
        message_node = message_entity
        
        # 6. Processa e envia mensagem
        await self.process_plaintext_node_and_send(message_node)
        
        logger.info(f"Mensagem enviada para {to_jid}: {text[:50]}...")
        return message_id
    
    async def process_plaintext_node_and_send(
        self,
        node: ProtocolNode,
        retry_receipt_entity: Optional[ProtocolNode] = None
    ) -> None:
        """
        Processa node de mensagem plaintext e envia.
        
        Equivalente ao processPlaintextNodeAndSend() do zowsuplib.
        
        Args:
            node: ProtocolNode da mensagem (com <proto> ainda não criptografado)
            retry_receipt_entity: Receipt de retry (se for reenvio)
        """
        to_jid = node.get_attribute("to")
        proto_node = node.get_child("proto")
        if not proto_node:
            raise ValueError("Node de mensagem deve ter <proto>")
        proto_bytes = proto_node.data
        
        # Verifica múltiplos destinos ("," em node["to"])
        if "," in to_jid:
            # Múltiplos destinos - split e envia para todos
            jids = [j.strip() for j in to_jid.split(",")]
            logger.info(f"Múltiplos destinos detectados: {len(jids)} destinatários")
            # Define o primeiro como destino principal
            node.set_attribute("to", jids[0])
            await self.ensure_sessions_and_send_to_contacts(node, jids)
        else:
            # Destino único
            account = to_jid.split('@')[0]
            is_group = self._is_group_jid(to_jid)
            
            if is_group:
                # Envia para grupo
                await self._send_to_group(node, proto_bytes, retry_receipt_entity)
            else:
                # Contato individual
                if ":" in account:
                    # Device específico (ex: 123456789:0)
                    jids = [to_jid]
                    await self.ensure_sessions_and_send_to_contacts(node, jids)
                elif "lid" in to_jid:
                    # LID (Linked ID)
                    jids = [to_jid]
                    await self.ensure_sessions_and_send_to_contacts(node, jids)
                else:
                    # Precisa sincronizar dispositivos primeiro
                    # Obtém todas as sessões existentes para este recipient
                    recipient_id = account
                    session_jids = await self.axolotl_manager.get_all_session_usernames(recipient_id)
                    
                    if session_jids:
                        # Tem sessões, envia para elas
                        await self.ensure_sessions_and_send_to_contacts(node, session_jids)
                    else:
                        # Não tem sessão, sincroniza dispositivos e obtém chaves
                        await self._sync_devices_and_send(node, proto_bytes, to_jid)
    
    async def send_text(
        self,
        to: str,
        text: str,
        message_id: Optional[str] = None
    ) -> str:
        """
        Envia mensagem de texto seguindo o fluxo completo do zowsuplib.
        
        Fluxo:
        1. Validações de segurança (conta restrita, limite diário)
        2. Verifica e sincroniza contato se necessário (assure_contacts_and_send)
        3. Cria node de mensagem com <proto> (sem criptografar ainda)
        4. Processa mensagem (process_plaintext_node_and_send)
        5. Sincroniza dispositivos se necessário
        6. Verifica sessões e obtém chaves se necessário
        7. Criptografa para cada dispositivo
        8. Adiciona reporting token, device-identity, etc.
        9. Envia
        
        Args:
            to: JID do destinatário (pode ser múltiplos separados por ",")
            text: Texto da mensagem
            message_id: ID da mensagem (gerado se None)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        # Destino único
        return await self.assure_contacts_and_send(to, text, message_id)
    
    async def send_image(
        self,
        to: str,
        file_path_or_url: str,
        caption: Optional[str] = None,
        message_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Envia imagem seguindo o fluxo completo do zowsuplib.
        
        Fluxo:
        1. Processa imagem (dimensões, thumbnail, SHA256)
        2. Gera media_key e criptografa imagem
        3. Obtém media connection
        4. Faz upload HTTP
        5. Constrói ImageMessage protobuf
        6. Envia usando fluxo existente
        
        Args:
            to: JID do destinatário
            file_path_or_url: Caminho do arquivo de imagem ou URL
            caption: Legenda da imagem (opcional)
            message_id: ID da mensagem (gerado se None)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        # Usa ImageBuilder para upload
        from .builders.image_builder import ImageBuilder
        
        builder = await ImageBuilder.from_filepath(
            file_path_or_url=file_path_or_url,
            media_cipher=self._media_cipher,
            media_uploader=self._media_uploader,
            media_connection=self._media_connection,
            caption=caption,
            progress_callback=progress_callback
        )
        
        # Obtém JID do remetente
        from_jid = f"{self.account_id}@{YowConstants.WHATSAPP_SERVER}"
        
        # Faz upload e constrói ImageMessage protobuf
        image_msg = await builder.upload_and_build(to, from_jid)
        
        # Extrai dados do protobuf
        url = image_msg.url
        direct_path = image_msg.direct_path if image_msg.direct_path else None
        mimetype = image_msg.mimetype
        file_sha256 = image_msg.file_sha256
        file_length = image_msg.file_length
        media_key = image_msg.media_key
        media_key_timestamp = image_msg.media_key_timestamp
        file_enc_sha256 = image_msg.file_enc_sha256
        width = image_msg.width
        height = image_msg.height
        jpeg_thumbnail = image_msg.jpeg_thumbnail if image_msg.jpeg_thumbnail else None
        
        # Gera message_id se não fornecido
        if not message_id:
            message_id = self._message_builder._generate_message_id()
        
        # Garante que 'to' tenha formato correto
        if "@" not in to:
            to = f"{to}@{YowConstants.WHATSAPP_SERVER}"
        
        # Importa classes necessárias
        from ..protocol.entities.attributes import (
            DownloadableMediaMessageAttributes,
            ImageAttributes,
            MessageMetaAttributes,
        )
        from ..protocol.entities.media import (
            ImageDownloadableMediaMessageProtocolEntity,
        )
        
        # Cria DownloadableMediaMessageAttributes
        downloadable_attrs = DownloadableMediaMessageAttributes(
            mimetype=mimetype,
            file_length=file_length,
            file_sha256=file_sha256,
            media_key=media_key,
            media_key_timestamp=media_key_timestamp,
            file_enc_sha256=file_enc_sha256,
            url=url,
            direct_path=direct_path
        )
        
        # Cria ImageAttributes
        image_attrs = ImageAttributes(
            downloadable_attrs,
            width,
            height,
            caption,
            jpeg_thumbnail
        )
        
        # Cria MessageMetaAttributes
        message_meta_attrs = MessageMetaAttributes(
            id=message_id,
            recipient=to,
            fromMe=True,
            timestamp=int(time.time())
        )
        
        # Cria Protocol Entity
        entity = ImageDownloadableMediaMessageProtocolEntity(
            image_attrs,
            message_meta_attrs
        )
        
        # Converte para ProtocolNode
        message_node = entity.to_protocol_node()
        
        # Extrai proto_bytes do node <proto>
        proto_node = None
        for child in message_node.children:
            if child.tag == "proto":
                proto_node = child
                break
        
        if not proto_node or not proto_node.data:
            raise ValueError("Falha ao obter dados protobuf do Protocol Entity")
        
        proto_bytes = proto_node.data
        
        # Envia usando fluxo existente
        await self._send_to_contact(message_node, proto_bytes, to)
        
        return message_id
    
    async def send_media_direct(
        self,
        to: str,
        media_type: str,
        url: str,
        mimetype: str,
        file_sha256: bytes,
        file_length: int,
        media_key: bytes,
        file_enc_sha256: bytes,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        direct_path: Optional[str] = None,
        caption: Optional[str] = None,
        jpeg_thumbnail: Optional[bytes] = None,
        media_key_timestamp: Optional[int] = None,
        message_id: Optional[str] = None,
        # Opções específicas por tipo de mídia
        ptt: bool = False,
        waveform: Optional[bytes] = None,
        duration: Optional[int] = None,
        file_name: Optional[str] = None,
        **options: Any
    ) -> str:
        """
        Envia mídia diretamente usando valores já processados, sem fazer upload.
        
        Útil quando você já tem os dados do upload (URL, direct_path, etc.)
        e quer apenas enviar a mensagem.
        
        Agora usa as novas Protocol Entities seguindo o padrão do zowsuplib.
        
        Args:
            to: JID do destinatário
            media_type: Tipo de mídia ("image", "video", "audio", "document", "sticker")
            url: URL da mídia no servidor WhatsApp
            mimetype: Tipo MIME da mídia (ex: "image/jpeg")
            file_sha256: Hash SHA256 do arquivo original (32 bytes)
            file_length: Tamanho do arquivo em bytes
            media_key: Chave de mídia usada para criptografia (32 bytes)
            file_enc_sha256: Hash SHA256 dos dados criptografados (32 bytes)
            width: Largura (para imagens/vídeos/stickers)
            height: Altura (para imagens/vídeos/stickers)
            direct_path: Caminho direto da mídia (opcional)
            caption: Legenda da mídia (opcional, não aplicável para stickers)
            jpeg_thumbnail: Thumbnail JPEG (opcional, bytes)
            media_key_timestamp: Timestamp da media_key (opcional, padrão: agora)
            message_id: ID da mensagem (gerado se None)
            # Opções específicas por tipo:
            ptt: Se True, envia áudio como push-to-talk (voice message)
            waveform: Waveform para áudio PTT (100 bytes)
            duration: Duração em segundos (para áudio/vídeo)
            file_name: Nome do arquivo (para documentos)
            **options: Outras opções específicas por tipo de mídia
        
        Returns:
            ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        if media_type not in ("image", "video", "audio", "document", "sticker"):
            raise ValueError(f"media_type deve ser um de: image, video, audio, document, sticker. Recebido: {media_type}")
        
        import time
        from ..protocol.entities.attributes import (
            DownloadableMediaMessageAttributes,
            ImageAttributes,
            VideoAttributes,
            AudioAttributes,
            DocumentAttributes,
            StickerAttributes,
            MessageMetaAttributes,
            MessageAttributes,
        )
        from ..protocol.entities.media import (
            ImageDownloadableMediaMessageProtocolEntity,
            VideoDownloadableMediaMessageProtocolEntity,
            AudioDownloadableMediaMessageProtocolEntity,
            DocumentDownloadableMediaMessageProtocolEntity,
            StickerDownloadableMediaMessageProtocolEntity,
        )
        
        # Gera message_id se não fornecido
        if not message_id:
            message_id = self._message_builder._generate_message_id()
        
        # Garante que 'to' tenha formato correto
        if "@" not in to:
            to = f"{to}@{YowConstants.WHATSAPP_SERVER}"
        
        # Cria DownloadableMediaMessageAttributes
        downloadable_attrs = DownloadableMediaMessageAttributes(
            mimetype=mimetype,
            file_length=file_length,
            file_sha256=file_sha256,
            media_key=media_key,
            media_key_timestamp=media_key_timestamp if media_key_timestamp is not None else int(time.time()),
            file_enc_sha256=file_enc_sha256,
            url=url,
            direct_path=direct_path
        )
        
        # Cria MessageMetaAttributes
        message_meta_attrs = MessageMetaAttributes(
            id=message_id,
            recipient=to,
            fromMe=True,
            timestamp=int(time.time())
        )
        
        # Cria Protocol Entity baseado no tipo de mídia
        entity = None
        
        if media_type == "image":
            if width is None or height is None:
                raise ValueError("width e height são obrigatórios para imagens")
            
            image_attrs = ImageAttributes(
                downloadable_attrs,
                width,
                height,
                caption,
                jpeg_thumbnail
            )
            entity = ImageDownloadableMediaMessageProtocolEntity(image_attrs, message_meta_attrs)
        
        elif media_type == "audio":
            audio_attrs = AudioAttributes(
                downloadable_attrs,
                duration or 0,
                ptt,
                None,  # streaming_sidecar
                waveform
            )
            entity = AudioDownloadableMediaMessageProtocolEntity(audio_attrs, message_meta_attrs)
        
        elif media_type == "video":
            if width is None or height is None:
                raise ValueError("width e height são obrigatórios para vídeos")
            
            video_attrs = VideoAttributes(
                downloadable_attrs,
                width,
                height,
                duration or 0,
                caption,
                False,  # gif_playback
                jpeg_thumbnail,
                0,  # gif_attribution
                None  # streaming_sidecar
            )
            entity = VideoDownloadableMediaMessageProtocolEntity(video_attrs, message_meta_attrs)
        
        elif media_type == "document":
            doc_attrs = DocumentAttributes(
                downloadable_attrs,
                file_name or "",
                file_length,
                None,  # title
                None,  # page_count
                jpeg_thumbnail,
                caption
            )
            entity = DocumentDownloadableMediaMessageProtocolEntity(doc_attrs, message_meta_attrs)
        
        elif media_type == "sticker":
            if width is None or height is None:
                raise ValueError("width e height são obrigatórios para stickers")
            
            sticker_attrs = StickerAttributes(
                downloadable_attrs,
                width,
                height,
                jpeg_thumbnail,  # png_thumbnail (aceita bytes)
                options.get("is_animated", False),
                None,  # sticker_sent_ts (será gerado automaticamente)
                options.get("is_avatar", False),
                options.get("is_ai_sticker", False),
                options.get("is_lottie", False)
            )
            entity = StickerDownloadableMediaMessageProtocolEntity(sticker_attrs, message_meta_attrs)
        
        if entity is None:
            raise ValueError(f"Falha ao criar Protocol Entity para media_type: {media_type}")
        
        # Converte para ProtocolNode
        message_node = entity.to_protocol_node()
        
        # Extrai proto_bytes do node <proto>
        proto_node = None
        for child in message_node.children:
            if child.tag == "proto":
                proto_node = child
                break
        
        if not proto_node or not proto_node.data:
            raise ValueError("Falha ao obter dados protobuf do Protocol Entity")
        
        proto_bytes = proto_node.data
        
        # Envia usando fluxo existente
        await self._send_to_contact(message_node, proto_bytes, to)
        
        return message_id
    
    async def send_audio(
        self,
        to: str,
        file_path_or_url: str,
        ptt: bool = False,
        message_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Envia áudio seguindo o fluxo completo do zowsuplib.
        
        Args:
            to: JID do destinatário
            file_path_or_url: Caminho do arquivo de áudio ou URL
            ptt: Se True, envia como push-to-talk (voice message)
            message_id: ID da mensagem (gerado se None)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        from .builders.audio_builder import AudioBuilder
        
        builder = await AudioBuilder.from_filepath(
            file_path_or_url=file_path_or_url,
            media_cipher=self._media_cipher,
            media_uploader=self._media_uploader,
            media_connection=self._media_connection,
            ptt=ptt,
            progress_callback=progress_callback
        )
        
        from_jid = f"{self.account_id}@{YowConstants.WHATSAPP_SERVER}"
        audio_msg = await builder.upload_and_build(to, from_jid)
        
        # Extrai dados do protobuf
        url = audio_msg.url
        direct_path = audio_msg.direct_path if audio_msg.direct_path else None
        mimetype = audio_msg.mimetype
        file_sha256 = audio_msg.file_sha256
        file_length = audio_msg.file_length
        media_key = audio_msg.media_key
        media_key_timestamp = audio_msg.media_key_timestamp
        file_enc_sha256 = audio_msg.file_enc_sha256
        duration = audio_msg.seconds if hasattr(audio_msg, 'seconds') else 0
        waveform = audio_msg.waveform if hasattr(audio_msg, 'waveform') and audio_msg.waveform else None
        
        if not message_id:
            message_id = self._message_builder._generate_message_id()
        
        # Garante que 'to' tenha formato correto
        if "@" not in to:
            to = f"{to}@{YowConstants.WHATSAPP_SERVER}"
        
        # Importa classes necessárias
        from ..protocol.entities.attributes import (
            DownloadableMediaMessageAttributes,
            AudioAttributes,
            MessageMetaAttributes,
        )
        from ..protocol.entities.media import (
            AudioDownloadableMediaMessageProtocolEntity,
        )
        
        # Cria DownloadableMediaMessageAttributes
        downloadable_attrs = DownloadableMediaMessageAttributes(
            mimetype=mimetype,
            file_length=file_length,
            file_sha256=file_sha256,
            media_key=media_key,
            media_key_timestamp=media_key_timestamp,
            file_enc_sha256=file_enc_sha256,
            url=url,
            direct_path=direct_path
        )
        
        # Cria AudioAttributes
        audio_attrs = AudioAttributes(
            downloadable_attrs,
            duration,
            ptt,
            None,  # streaming_sidecar
            waveform
        )
        
        # Cria MessageMetaAttributes
        message_meta_attrs = MessageMetaAttributes(
            id=message_id,
            recipient=to,
            fromMe=True,
            timestamp=int(time.time())
        )
        
        # Cria Protocol Entity
        entity = AudioDownloadableMediaMessageProtocolEntity(
            audio_attrs,
            message_meta_attrs
        )
        
        # Converte para ProtocolNode
        message_node = entity.to_protocol_node()
        
        # Extrai proto_bytes do node <proto>
        proto_node = None
        for child in message_node.children:
            if child.tag == "proto":
                proto_node = child
                break
        
        if not proto_node or not proto_node.data:
            raise ValueError("Falha ao obter dados protobuf do Protocol Entity")
        
        proto_bytes = proto_node.data
        
        await self._send_to_contact(message_node, proto_bytes, to)
        
        return message_id
    
    async def send_document(
        self,
        to: str,
        file_path_or_url: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        message_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Envia documento seguindo o fluxo completo do zowsuplib.
        
        Args:
            to: JID do destinatário
            file_path_or_url: Caminho do arquivo do documento ou URL
            filename: Nome do arquivo (opcional, usa basename se None)
            caption: Legenda do documento (opcional)
            message_id: ID da mensagem (gerado se None)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        from .builders.document_builder import DocumentBuilder
        
        builder = await DocumentBuilder.from_filepath(
            file_path_or_url=file_path_or_url,
            media_cipher=self._media_cipher,
            media_uploader=self._media_uploader,
            media_connection=self._media_connection,
            filename=filename,
            caption=caption,
            progress_callback=progress_callback
        )
        
        from_jid = f"{self.account_id}@{YowConstants.WHATSAPP_SERVER}"
        doc_msg = await builder.upload_and_build(to, from_jid)
        
        # Extrai dados do protobuf
        url = doc_msg.url
        direct_path = doc_msg.direct_path if doc_msg.direct_path else None
        mimetype = doc_msg.mimetype
        file_sha256 = doc_msg.file_sha256
        file_length = doc_msg.file_length
        media_key = doc_msg.media_key
        media_key_timestamp = doc_msg.media_key_timestamp
        file_enc_sha256 = doc_msg.file_enc_sha256
        file_name = doc_msg.file_name
        jpeg_thumbnail = doc_msg.jpeg_thumbnail if doc_msg.jpeg_thumbnail else None
        caption_from_proto = doc_msg.caption if doc_msg.caption else caption
        
        if not message_id:
            message_id = self._message_builder._generate_message_id()
        
        # Garante que 'to' tenha formato correto
        if "@" not in to:
            to = f"{to}@{YowConstants.WHATSAPP_SERVER}"
        
        # Importa classes necessárias
        from ..protocol.entities.attributes import (
            DownloadableMediaMessageAttributes,
            DocumentAttributes,
            MessageMetaAttributes,
        )
        from ..protocol.entities.media import (
            DocumentDownloadableMediaMessageProtocolEntity,
        )
        
        # Cria DownloadableMediaMessageAttributes
        downloadable_attrs = DownloadableMediaMessageAttributes(
            mimetype=mimetype,
            file_length=file_length,
            file_sha256=file_sha256,
            media_key=media_key,
            media_key_timestamp=media_key_timestamp,
            file_enc_sha256=file_enc_sha256,
            url=url,
            direct_path=direct_path
        )
        
        # Cria DocumentAttributes
        doc_attrs = DocumentAttributes(
            downloadable_attrs,
            file_name,
            file_length,
            None,  # title
            None,  # page_count
            jpeg_thumbnail,
            caption_from_proto
        )
        
        # Cria MessageMetaAttributes
        message_meta_attrs = MessageMetaAttributes(
            id=message_id,
            recipient=to,
            fromMe=True,
            timestamp=int(time.time())
        )
        
        # Cria Protocol Entity
        entity = DocumentDownloadableMediaMessageProtocolEntity(
            doc_attrs,
            message_meta_attrs
        )
        
        # Converte para ProtocolNode
        message_node = entity.to_protocol_node()
        
        # Extrai proto_bytes do node <proto>
        proto_node = None
        for child in message_node.children:
            if child.tag == "proto":
                proto_node = child
                break
        
        if not proto_node or not proto_node.data:
            raise ValueError("Falha ao obter dados protobuf do Protocol Entity")
        
        proto_bytes = proto_node.data
        
        await self._send_to_contact(message_node, proto_bytes, to)
        
        return message_id
    
    async def send_sticker(
        self,
        to: str,
        file_path_or_url: str,
        is_animated: bool = False,
        is_avatar: bool = False,
        is_ai_sticker: bool = False,
        is_lottie: bool = False,
        message_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Envia sticker seguindo o fluxo completo do zowsuplib.
        
        Args:
            to: JID do destinatário
            file_path_or_url: Caminho do arquivo de sticker ou URL
            is_animated: Se é sticker animado
            is_avatar: Se é avatar sticker
            is_ai_sticker: Se é AI sticker
            is_lottie: Se é Lottie sticker
            message_id: ID da mensagem (gerado se None)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        from .builders.sticker_builder import StickerBuilder
        
        builder = await StickerBuilder.from_filepath(
            file_path_or_url=file_path_or_url,
            media_cipher=self._media_cipher,
            media_uploader=self._media_uploader,
            media_connection=self._media_connection,
            is_animated=is_animated,
            is_avatar=is_avatar,
            is_ai_sticker=is_ai_sticker,
            is_lottie=is_lottie,
            progress_callback=progress_callback
        )
        
        from_jid = f"{self.account_id}@{YowConstants.WHATSAPP_SERVER}"
        sticker_msg = await builder.upload_and_build(to, from_jid)
        
        # Extrai dados do protobuf
        url = sticker_msg.url
        direct_path = sticker_msg.direct_path if sticker_msg.direct_path else None
        mimetype = sticker_msg.mimetype
        file_sha256 = sticker_msg.file_sha256
        file_length = sticker_msg.file_length
        media_key = sticker_msg.media_key
        media_key_timestamp = sticker_msg.media_key_timestamp
        file_enc_sha256 = sticker_msg.file_enc_sha256
        width = sticker_msg.width
        height = sticker_msg.height
        png_thumbnail = None  # StickerMessage não tem thumbnail no protobuf
        
        if not message_id:
            message_id = self._message_builder._generate_message_id()
        
        # Garante que 'to' tenha formato correto
        if "@" not in to:
            to = f"{to}@{YowConstants.WHATSAPP_SERVER}"
        
        # Importa classes necessárias
        from ..protocol.entities.attributes import (
            DownloadableMediaMessageAttributes,
            StickerAttributes,
            MessageMetaAttributes,
        )
        from ..protocol.entities.media import (
            StickerDownloadableMediaMessageProtocolEntity,
        )
        
        # Cria DownloadableMediaMessageAttributes
        downloadable_attrs = DownloadableMediaMessageAttributes(
            mimetype=mimetype,
            file_length=file_length,
            file_sha256=file_sha256,
            media_key=media_key,
            media_key_timestamp=media_key_timestamp,
            file_enc_sha256=file_enc_sha256,
            url=url,
            direct_path=direct_path
        )
        
        # Cria StickerAttributes
        sticker_attrs = StickerAttributes(
            downloadable_attrs,
            width,
            height,
            png_thumbnail,
            is_animated,
            sticker_msg.sticker_sent_ts if hasattr(sticker_msg, 'sticker_sent_ts') else None,
            is_avatar,
            is_ai_sticker,
            is_lottie
        )
        
        # Cria MessageMetaAttributes
        message_meta_attrs = MessageMetaAttributes(
            id=message_id,
            recipient=to,
            fromMe=True,
            timestamp=int(time.time())
        )
        
        # Cria Protocol Entity
        entity = StickerDownloadableMediaMessageProtocolEntity(
            sticker_attrs,
            message_meta_attrs
        )
        
        # Converte para ProtocolNode
        message_node = entity.to_protocol_node()
        
        # Extrai proto_bytes do node <proto>
        proto_node = None
        for child in message_node.children:
            if child.tag == "proto":
                proto_node = child
                break
        
        if not proto_node or not proto_node.data:
            raise ValueError("Falha ao obter dados protobuf do Protocol Entity")
        
        proto_bytes = proto_node.data
        
        await self._send_to_contact(message_node, proto_bytes, to)
        
        return message_id
    
    def _is_group_jid(self, jid: str) -> bool:
        """Verifica se JID é de grupo"""
        return "-" in jid.split("@")[0] or "@g.us" in jid or "broadcast" in jid
    
    async def _check_account_restriction(self) -> bool:
        """
        Verifica se conta está restrita.
        
        Baseado em yowbot_layer._check_account_restriction()
        
        Returns:
            True se conta está restrita, False caso contrário
        """
        # Por enquanto, sempre retorna False (conta não restrita)
        # Pode ser implementado verificando no banco de dados ou configuração
        return False
    
    async def _check_daily_limit(self) -> bool:
        """
        Verifica limite diário de mensagens.
        
        Baseado em yowbot_layer._check_daily_limit()
        
        Returns:
            True se pode enviar (dentro do limite), False caso contrário
        """
        MAX_DAILY = 1000  # Configurável
        return self._daily_message_count < MAX_DAILY
    
    def _is_number_invalid(self, jid: str) -> bool:
        """
        Verifica se número está na lista de inválidos.
        
        Baseado em yowbot_layer._is_number_invalid()
        
        Args:
            jid: JID para verificar
            
        Returns:
            True se número é inválido, False caso contrário
        """
        # Por enquanto, sempre retorna False (número válido)
        # Pode ser implementado verificando no store ou lista de inválidos
        return False
    
    async def _check_rate_limit(self, jid: str, min_delay_seconds: float = 2.0) -> None:
        """
        Rate limiting entre mensagens.
        
        Baseado em yowbot_layer._check_rate_limit()
        
        Args:
            jid: JID do destinatário
            min_delay_seconds: Delay mínimo entre mensagens (padrão: 2.0s)
        """
        last_time = self._last_message_time.get(jid, 0)
        current_time = time.time()
        elapsed = current_time - last_time
        
        if elapsed < min_delay_seconds:
            wait_time = min_delay_seconds - elapsed
            logger.debug(f"Rate limit: aguardando {wait_time:.2f}s antes de enviar para {jid}")
            await asyncio.sleep(wait_time)
        
        self._last_message_time[jid] = time.time()
    
    async def _send_to_contact(self, message_node: ProtocolNode, proto_bytes: bytes, to_jid: str) -> None:
        """
        Envia mensagem para contato individual ou grupo.
        
        Fluxo baseado em AxolotlSendLayer.processPlaintextNodeAndSend():
        - Se grupo: chama _send_to_group()
        - Se contato: processa normalmente
        1. Verifica se precisa sincronizar dispositivos
        2. Verifica quais dispositivos têm sessão
        3. Obtém chaves para dispositivos sem sessão
        4. Criptografa para cada dispositivo
        5. Envia
        """
        # Verifica se é grupo
        is_group = self._is_group_jid(to_jid)
        
        if is_group:
            # Envia para grupo usando fluxo completo
            await self._send_to_group(message_node, proto_bytes, retry_receipt_entity=None)
            return
        
        # Contato individual - continua fluxo normal
        account = to_jid.split('@')[0]
        
        # Verifica se tem dispositivo específico (ex: 123456789:0)
        if ":" in account:
            # Dispositivo específico
            jids = [to_jid]
            await self._send_to_contacts_with_sessions(message_node, jids)
        elif "lid" in to_jid:
            # LID (Linked ID)
            jids = [to_jid]
            await self._send_to_contacts_with_sessions(message_node, jids)
        else:
            # Precisa sincronizar dispositivos primeiro
            recipient_id = account
            
            # Obtém todas as sessões existentes para este recipient
            session_jids = await self.axolotl_manager.get_all_session_usernames(recipient_id)
            
            if session_jids:
                # Tem sessões, envia para elas
                await self._send_to_contacts_with_sessions(message_node, session_jids)
            else:
                # Não tem sessão, sincroniza dispositivos e obtém chaves
                await self._sync_devices_and_send(message_node, proto_bytes, to_jid)
    
    async def ensure_sessions_and_send_to_contacts(
        self, 
        message_node: ProtocolNode, 
        jids: list[str],
        retry_count: int = 0
    ) -> None:
        """
        Garante que há sessões para os JIDs e envia mensagem.
        
        Equivalente ao ensureSessionsAndSendToContacts() do zowsuplib.
        Separa JIDs com sessão dos sem sessão, obtém chaves se necessário.
        
        Args:
            message_node: ProtocolNode da mensagem (com <proto>)
            jids: Lista de JIDs para enviar
            retry_count: Contador de retry (para reenvios)
        """
        logger.debug(f"ensure_sessions_and_send_to_contacts: {len(jids)} JIDs, retry_count={retry_count}")
        
        # Obtém proto_bytes do node
        proto_node = message_node.get_child("proto")
        if not proto_node:
            raise ValueError("Node de mensagem deve ter <proto>")
        proto_bytes = proto_node.data
        
        # Separa JIDs com sessão dos sem sessão
        all_jids = []
        jids_no_session = []
        
        for jid in jids:
            recipient_id = jid.split('@')[0]
            if await self.axolotl_manager.session_exists(recipient_id):
                all_jids.append(jid)
            else:
                jids_no_session.append(jid)
        
        async def on_get_keys_success(node, success_jids, errors):
            """Callback quando chaves são obtidas com sucesso"""
            if errors:
                # Processa erros
                for jid, error in errors.items():
                    logger.error(f"Erro ao obter chaves para {jid}: {error}")
                # Continua mesmo com erros (envia para os que funcionaram)
            
            # Adiciona JIDs com sucesso
            all_jids.extend(success_jids)
            
            # Envia para todos os JIDs que têm sessão agora
            if len(all_jids) > 0:
                category = node.get_attribute("category")
                if category == "peer":
                    await self.send_to_peer_with_sessions(node, all_jids[0])
                else:
                    await self._send_to_contacts_with_sessions(node, all_jids, retry_count)
            else:
                logger.warning("Nenhum JID com sessão disponível após obter chaves")
        
        # Se há JIDs sem sessão, obtém chaves
        if len(jids_no_session) > 0:
            logger.debug(f"Obtendo chaves para {len(jids_no_session)} JIDs sem sessão")
            # Obtém chaves para todos os JIDs sem sessão
            success_jids, error_jids = await self._get_keys_for_jids(jids_no_session)
            
            # Processa resultado
            await on_get_keys_success(message_node, success_jids, error_jids)
        else:
            # Todos os JIDs já têm sessão
            category = message_node.get_attribute("category")
            if category == "peer":
                await self.send_to_peer_with_sessions(message_node, all_jids[0] if all_jids else None)
            else:
                await self._send_to_contacts_with_sessions(message_node, all_jids, retry_count)
    
    async def _get_keys_for_jids(
        self,
        jids: List[str],
        reason: Optional[str] = None
    ) -> Tuple[List[str], Dict[str, Exception]]:
        """
        Obtém chaves para múltiplos JIDs.
        
        Args:
            jids: Lista de JIDs
            reason: Razão para obter chaves (opcional)
        
        Returns:
            Tuple[List[str], Dict[str, Exception]]: (success_jids, error_jids)
        """
        all_success = []
        all_errors = {}
        
        for jid in jids:
            recipient_id = jid.split('@')[0]
            success_jids, error_jids = await self._get_keys_for_recipient(recipient_id, reason=reason)
            all_success.extend(success_jids)
            all_errors.update(error_jids)
        
        return all_success, all_errors
    
    async def _send_to_contacts_with_sessions(
        self, 
        message_node: ProtocolNode, 
        jids: list[str],
        retry_count: int = 0
    ) -> None:
        """
        Envia mensagem para múltiplos contatos/dispositivos que têm sessão.
        
        Baseado em AxolotlSendLayer.sendToContactsWithSessions()
        
        Args:
            message_node: ProtocolNode da mensagem (com <proto>)
            jids: Lista de JIDs para enviar
            retry_count: Contador de retry (para reenvios)
        """
        # Obtém proto_bytes do node
        proto_node = message_node.get_child("proto")
        if not proto_node:
            raise ValueError("Node de mensagem deve ter <proto>")
        proto_bytes = proto_node.data
        
        # Obtém mediatype do proto node
        mediatype = proto_node.get_attribute("mediatype") if proto_node else "text"
        
        # Obtém tctoken se necessário
        target_jid = message_node.get_attribute("to")
        tctoken = None
        if hasattr(self, 'axolotl_manager') and hasattr(self.axolotl_manager, '_store'):
            tctoken = await self.axolotl_manager._store.getTcToken(target_jid)
        
        enc_entities = []
        participant = jids[0] if len(jids) == 1 and retry_count > 0 else None
        
        for jid in jids:
            # Garante que jid é string
            if not isinstance(jid, str):
                logger.error(f"JID inválido (não é string): {jid} (tipo: {type(jid)})")
                continue
            
            logger.debug(f"JID: {jid}")

            # CORREÇÃO: Converte JID para formato do zowsuplib
            # get_all_session_usernames() retorna formato "recipient_id.recipient_type:device_id"
            # mas zowsuplib espera JID completo "recipient_id@s.whatsapp.net" no node <to>
            if "@" in jid:
                # JID completo: extrai apenas o recipient_id para encrypt()
                recipient_id = jid.split('@')[0]
                # Remove device_id se existir (ex: "559885700260:0" -> "559885700260")
                recipient_id = recipient_id.split(':')[0] if ':' in recipient_id else recipient_id
                # JID para o node <to> (zowsuplib usa JID completo)
                to_jid_for_node = jid
            else:
                # Formato interno "recipient_id.recipient_type:device_id"
                # Extrai apenas o recipient_id (parte antes do primeiro ponto)
                recipient_id = jid.split('.')[0]
                # Converte para JID completo no formato do zowsuplib
                to_jid_for_node = f"{recipient_id}@s.whatsapp.net"
            
            # Criptografa para este dispositivo (usa recipient_id interno)
            ciphertext = await self.axolotl_manager.encrypt(recipient_id, proto_bytes)
            
            # Identifica tipo
            if isinstance(ciphertext, PreKeyWhisperMessage):
                enc_type = EncEntity.TYPE_PKMSG
            elif isinstance(ciphertext, WhisperMessage):
                enc_type = EncEntity.TYPE_MSG
            else:
                enc_type = EncEntity.TYPE_MSG
            
            # Cria node <enc> usando EncEntity helper
            # Para contatos individuais, usa <to> wrapper dentro de <participants>
            # CORREÇÃO: usa to_jid_for_node (JID completo) no formato do zowsuplib
            enc_node = EncEntity.create_enc_node(
                enc_type=enc_type,
                ciphertext=ciphertext.serialize(),
                mediatype=mediatype,
                jid=to_jid_for_node,  # JID completo no formato do zowsuplib
                count=str(retry_count) if retry_count > 0 else None
            )
            
            enc_entities.append(enc_node)
        
        # Constrói node final usando EncryptedMessageBuilder
        message_node = EncryptedMessageBuilder.build_encrypted_message(
            message_node=message_node,
            enc_entities=enc_entities,
            participant=participant
        )
        
        # Adiciona elementos extras (reporting, device-identity, tctoken, etc.)
        await self._add_message_extras(message_node, tctoken=tctoken)
        
        # Enfileira mensagem antes de enviar (para retry)
        self._enqueue_sent_message(message_node)
        
        # Envia
        await self._send_protocol_node(message_node)
    
    async def send_to_peer_with_sessions(
        self,
        message_node: ProtocolNode,
        jid: Optional[str] = None
    ) -> None:
        """
        Envia mensagem peer-to-peer (category="peer").
        
        Baseado em AxolotlSendLayer.sendToPeerWithSessions()
        
        Args:
            message_node: ProtocolNode da mensagem (com <proto>)
            jid: JID do destinatário (se None, usa do node)
        """
        if not jid:
            jid = message_node.get_attribute("to")
        
        if not jid:
            raise ValueError("JID não especificado")
        
        # Obtém proto_bytes do node
        proto_node = message_node.get_child("proto")
        if not proto_node:
            raise ValueError("Node de mensagem deve ter <proto>")
        proto_bytes = proto_node.data
        
        # Obtém mediatype
        mediatype = proto_node.get_attribute("mediatype") if proto_node else "text"
        
        recipient_id = jid.split('@')[0]
        
        # Criptografa mensagem
        ciphertext = await self.axolotl_manager.encrypt(recipient_id, proto_bytes)
        
        # Identifica tipo
        if isinstance(ciphertext, PreKeyWhisperMessage):
            enc_type = EncEntity.TYPE_PKMSG
        elif isinstance(ciphertext, WhisperMessage):
            enc_type = EncEntity.TYPE_MSG
        else:
            enc_type = EncEntity.TYPE_MSG
        
        # Cria node <enc> - para peer, não usa <to> wrapper e jid=None
        enc_entities = [
            EncEntity.create_enc_node(
                enc_type=enc_type,
                ciphertext=ciphertext.serialize(),
                mediatype=mediatype,
                jid=None  # Para peer, sempre None
            )
        ]
        
        # Constrói node final
        message_node = EncryptedMessageBuilder.build_encrypted_message(
            message_node=message_node,
            enc_entities=enc_entities,
            participant=None
        )
        
        # Obtém tctoken se necessário
        tctoken = None
        if hasattr(self, 'axolotl_manager') and hasattr(self.axolotl_manager, '_store'):
            tctoken = await self.axolotl_manager._store.getTcToken(jid)
        
        # Adiciona elementos extras
        await self._add_message_extras(message_node, tctoken=tctoken)
        
        # Enfileira mensagem antes de enviar (para retry)
        self._enqueue_sent_message(message_node)
        
        # Envia
        await self._send_protocol_node(message_node)
    
    async def _sync_devices_and_send(
        self, 
        message_node: ProtocolNode, 
        proto_bytes: bytes, 
        to_jid: str
    ) -> None:
        """
        Sincroniza dispositivos do contato e envia mensagem.
        
        Baseado em AxolotlSendLayer.sendToContact() com sincronização de dispositivos.
        """
        recipient_id = to_jid.split('@')[0]
        
        try:
            # Sincroniza dispositivos usando ContactHandler
            if self.contact_handler:
                devices = await self.contact_handler.sync_devices([to_jid])
                if devices:
                    # Envia para todos os dispositivos encontrados
                    await self.ensure_sessions_and_send_to_contacts(message_node, devices)
                    return
            
            # Se não conseguiu sincronizar ou não há handler, tenta enviar como PKMSG
            await self._send_as_pkmsg(message_node, proto_bytes, to_jid)
        
        except Exception as e:
            logger.warning(f"Erro ao sincronizar dispositivos, enviando como PKMSG: {e}")
            await self._send_as_pkmsg(message_node, proto_bytes, to_jid)
    
    async def _send_as_pkmsg(self, message_node: ProtocolNode, proto_bytes: bytes, to_jid: str) -> None:
        """
        Envia mensagem como PKMSG (quando não há sessão).
        
        Baseado em AxolotlSendLayer.sendToContactAsPkmsg()
        """
        
        recipient_id = to_jid.split('@')[0]
        
        # Obtém chaves antes de criptografar
        await self._get_keys_for_recipient(recipient_id)
        
        try:
            # Obtém mediatype do proto node
            proto_node = message_node.get_child("proto")
            mediatype = proto_node.get_attribute("mediatype") if proto_node else "text"
            
            # Tenta criptografar (vai criar sessão se necessário)
            ciphertext = await self.axolotl_manager.encrypt(recipient_id, proto_bytes)
            
            # Identifica tipo
            if isinstance(ciphertext, PreKeyWhisperMessage):
                enc_type = EncEntity.TYPE_PKMSG
            else:
                enc_type = EncEntity.TYPE_MSG
            
            # Cria node <enc> usando EncEntity helper
            enc_node = EncEntity.create_enc_node(
                enc_type=enc_type,
                ciphertext=ciphertext.serialize(),
                mediatype=mediatype,
                jid=recipient_id
            )
            
            # Constrói node final usando EncryptedMessageBuilder
            message_node = EncryptedMessageBuilder.build_encrypted_message(
                message_node=message_node,
                enc_entities=[enc_node],
                participant=None
            )
            
            # Obtém tctoken se necessário
            tctoken = None
            if hasattr(self, 'axolotl_manager') and hasattr(self.axolotl_manager, '_store'):
                tctoken = await self.axolotl_manager._store.getTcToken(to_jid)
            
            # Adiciona elementos extras
            await self._add_message_extras(message_node, tctoken=tctoken)
            
            # Enfileira mensagem antes de enviar (para retry)
            self._enqueue_sent_message(message_node)
            
            # Envia
            await self._send_protocol_node(message_node)
        
        except (IndexError, Exception) as e:
            # Se falhar por falta de sessão/prekeys, loga erro mais claro
            error_msg = str(e)
            if "bytearray index out of range" in error_msg or "NoSessionException" in error_msg or "No session" in error_msg:
                logger.error(
                    f"Não é possível enviar mensagem para {recipient_id}: "
                    f"sessão não existe e não foi possível criar automaticamente. "
                    f"É necessário obter prekeys primeiro via IQ antes de enviar mensagem."
                )
                raise RuntimeError(
                    f"Não é possível enviar mensagem: sessão não existe para {recipient_id}. "
                    f"Obtenha prekeys primeiro usando sync_devices ou get_keys_for_recipient."
                ) from e
            raise
    
    async def _get_keys_for_recipient(
        self,
        recipient_id: str,
        reason: Optional[str] = None
    ) -> Tuple[List[str], Dict[str, Exception]]:
        """
        Obtém chaves para um recipient (prekeys, identity keys, etc.).
        
        CORREÇÃO: Verifica se já existe PKMSG pendente antes de solicitar.
        Baseado em AxolotlBaseLayer.getKeysFor()
        
        Args:
            recipient_id: ID do recipient (username ou JID completo)
            reason: Razão para obter chaves (opcional)
        
        Returns:
            Tuple[List[str], Dict[str, Exception]]: (success_jids, error_jids)
        """
        if "@" not in recipient_id:
            recipient_jid = f"{recipient_id}@{YowConstants.WHATSAPP_SERVER}"
        else:
            recipient_jid = recipient_id
        
        jids = [recipient_jid]
        
        logger.debug(f"Obtendo chaves para {recipient_jid}, reason={reason}")
        
        # Cria IQ para obter chaves
        iq_node = PrekeyBuilder.build_get_keys_iq(
            jids=jids,
            reason=reason,
            iq_id=None
        )
        
        iq_id = iq_node.get_attribute("id")
        
        # Cria future para aguardar resposta
        future = asyncio.Future()
        success_jids = []
        error_jids: Dict[str, Exception] = {}
        
        async def on_success(result_node: ProtocolNode):
            """Callback de sucesso"""
            try:
                # Extrai PreKeyBundle da resposta
                # Baseado em ResultGetKeysIqProtocolEntity.fromProtocolTreeNode()
                list_node = result_node.get_child("list")
                if not list_node:
                    logger.warning("Resposta de get keys sem node <list>")
                    future.set_result(([], {}))
                    return
                
                user_nodes = list_node.children
                for user_node in user_nodes:
                    jid = user_node.get_attribute("jid")
                    if not jid:
                        continue
                    
                    # Verifica se tem erro
                    error_child = user_node.get_child("error")
                    if error_child:
                        error_code = error_child.get_attribute("code")
                        error_text = error_child.get_attribute("text")
                        error_jids[jid] = Exception(f"Erro {error_code}: {error_text}")
                        continue
                    
                    # Extrai componentes do PreKeyBundle
                    registration_node = user_node.get_child("registration")
                    identity_node = user_node.get_child("identity")
                    signed_prekey_node = user_node.get_child("skey")
                    prekey_node = user_node.get_child("key")
                    
                    if not registration_node or not identity_node or not signed_prekey_node:
                        error_jids[jid] = Exception("Faltam parâmetros obrigatórios na resposta")
                        continue
                    
                    # Converte bytes para int
                    def _bytes_to_int(val):
                        if sys.version_info >= (3, 0):
                            val_enc = val.encode('latin-1') if type(val) is str else val
                        else:
                            val_enc = val
                        return int(binascii.hexlify(val_enc), 16)
                    
                    def _enc_str(string):
                        if sys.version_info >= (3, 0) and type(string) is str:
                            return string.encode('latin-1')
                        return string
                    
                    registration_id = _bytes_to_int(registration_node.data)
                    identity_key = IdentityKey(DjbECPublicKey(_enc_str(identity_node.data)))
                    
                    # Signed prekey
                    signed_prekey_id = _bytes_to_int(signed_prekey_node.get_child("id").data)
                    signed_prekey_pub = DjbECPublicKey(_enc_str(signed_prekey_node.get_child("value").data))
                    signed_prekey_sig = _enc_str(signed_prekey_node.get_child("signature").data)
                    
                    # Prekey (opcional)
                    prekey_id = None
                    prekey_public = None
                    if prekey_node:
                        prekey_id = _bytes_to_int(prekey_node.get_child("id").data)
                        prekey_public = DjbECPublicKey(_enc_str(prekey_node.get_child("value").data))
                    
                    # Cria PreKeyBundle
                    prekey_bundle = PreKeyBundle(
                        registration_id,
                        1,  # device_id
                        prekey_id,
                        prekey_public,
                        signed_prekey_id,
                        signed_prekey_pub,
                        signed_prekey_sig,
                        identity_key
                    )
                    
                    # Cria sessão
                    username = jid.split('@')[0]
                    try:
                        await self.axolotl_manager.create_session(username, prekey_bundle, autotrust=True)
                        success_jids.append(jid)
                        logger.info(f"Sessão criada para {jid}")
                    except exceptions.UntrustedIdentityException as e:
                        error_jids[jid] = e
                        logger.warning(f"Identity não confiável para {jid}: {e}")
                    except Exception as e:
                        error_jids[jid] = e
                        logger.error(f"Erro ao criar sessão para {jid}: {e}")
                
                if not future.done():
                    future.set_result((success_jids, error_jids))
                else:
                    logger.debug(f"Future já resolvida para IQ {iq_id}, ignorando set_result")
            
            except Exception as e:
                logger.error(f"Erro ao processar resposta de get keys: {e}", exc_info=True)
                if not future.done():
                    future.set_exception(e)
                else:
                    logger.debug(f"Future já resolvida para IQ {iq_id}, ignorando set_exception")
   
        async with self._pending_keys_lock:
            # Cria e registra future na fila
            self._pending_keys_requests[recipient_jid] = future
        
        timeout = 120
        
        try:
            # Registra callbacks e envia
            self._iq_response_processor.register_callback(iq_id, on_success, timeout=timeout)
            await self._send_protocol_node(iq_node)
            
            result = await asyncio.wait_for(future, timeout=timeout)
            
            # CORREÇÃO: Remove da fila após sucesso
            async with self._pending_keys_lock:
                if recipient_jid in self._pending_keys_requests:
                    # Verifica se é o mesmo future (pode ter sido substituído)
                    if self._pending_keys_requests[recipient_jid] == future:
                        del self._pending_keys_requests[recipient_jid]
                        logger.debug(f"PKMSG concluído para {recipient_jid}, removido da fila")
            
            return result
            
        except asyncio.TimeoutError:
            self._iq_response_processor.unregister_callback(iq_id)
            
            async with self._pending_keys_lock:
                if recipient_jid in self._pending_keys_requests:
                    if self._pending_keys_requests[recipient_jid] == future:
                        del self._pending_keys_requests[recipient_jid]
                        logger.debug(f"PKMSG timeout para {recipient_jid}, removido da fila")
            
            logger.error(f"Timeout ao obter chaves para {recipient_jid}")
            
            if not future.done():
                error_result = ([], {recipient_jid: Exception("Timeout ao obter chaves")})
                future.set_result(error_result)
            
            return ([], {recipient_jid: Exception("Timeout ao obter chaves")})
            
        except Exception as e:
            self._iq_response_processor.unregister_callback(iq_id)
            
            async with self._pending_keys_lock:
                if recipient_jid in self._pending_keys_requests:
                    if self._pending_keys_requests[recipient_jid] == future:
                        del self._pending_keys_requests[recipient_jid]
                        logger.debug(f"PKMSG erro para {recipient_jid}, removido da fila")
            
            logger.error(f"Erro ao obter chaves para {recipient_jid}: {e}")
            
            if not future.done():
                error_result = ([], {recipient_jid: e})
                future.set_result(error_result)
            
            return ([], {recipient_jid: e})
    
    async def _send_to_group(
        self,
        message_node: ProtocolNode,
        proto_bytes: bytes,
        retry_receipt_entity: Optional[ProtocolNode] = None
    ) -> None:
        """
        Envia mensagem para grupo seguindo fluxo completo do zowsuplib.
        
        Baseado em AxolotlSendLayer.sendToGroup() do zowsuplib.
        
        Fluxo:
        1. Verifica se sender key record existe
        2. Se não existe: cria, obtém participantes, distribui sender key
        3. Se existe: verifica retry e envia SKMSG (com distribution se necessário)
        
        Args:
            message_node: ProtocolNode da mensagem (com <proto>)
            proto_bytes: Bytes do protobuf (já extraído do node)
            retry_receipt_entity: Receipt de retry (se for reenvio)
        """
        group_jid = message_node.get_attribute("to")
        own_jid = f"{self.account_id}@{YowConstants.WHATSAPP_SERVER}"
        
        logger.debug(f"_send_to_group: group_jid={group_jid}, retry_receipt_entity={retry_receipt_entity is not None}")
        
        # Verifica se sender key record existe
        sender_key_record = await self.axolotl_manager.load_senderkey(group_jid)
        
        # Verifica se está vazio (usa isEmpty() do SenderKeyRecord)
        try:
            is_empty = sender_key_record.isEmpty() if sender_key_record else True
        except (AttributeError, TypeError):
            # Se não tem método isEmpty ou é None, considera vazio
            is_empty = True
        
        if is_empty:
            # Sender key não existe, precisa criar e distribuir
            logger.debug(f"Sender key não encontrado para grupo {group_jid}, criando e distribuindo...")
            
            # Casos especiais: status@broadcast e @broadcast
            if group_jid == "status@broadcast":
                # Para status@broadcast, obtém todos os contatos conhecidos
                logger.debug("Tentando obter contatos para status@broadcast")
                try:
                    if hasattr(self.axolotl_manager, '_store') and hasattr(self.axolotl_manager._store, 'getAllContact'):
                        jids = await self.axolotl_manager._store.getAllContact() if asyncio.iscoroutinefunction(self.axolotl_manager._store.getAllContact) else self.axolotl_manager._store.getAllContact()
                        logger.info(f"Enviando status para {len(jids)} contatos via status@broadcast")
                        await self.ensure_sessions_and_send_to_group(message_node, jids)
                        return
                    else:
                        logger.warning("Store não tem método getAllContact, enviando sem destinatários específicos")
                        await self.ensure_sessions_and_send_to_group(message_node, [])
                        return
                except Exception as e:
                    logger.error(f"Erro ao obter contatos para status@broadcast: {e}")
                    await self.ensure_sessions_and_send_to_group(message_node, [])
                    return
            
            elif group_jid.endswith("@broadcast"):
                # Para @broadcast, obtém participantes por BCID
                logger.debug(f"Obtendo participantes para broadcast: {group_jid}")
                try:
                    if hasattr(self.axolotl_manager, '_store') and hasattr(self.axolotl_manager._store, 'findParticipantsByBcid'):
                        jids = await self.axolotl_manager._store.findParticipantsByBcid(group_jid) if asyncio.iscoroutinefunction(self.axolotl_manager._store.findParticipantsByBcid) else self.axolotl_manager._store.findParticipantsByBcid(group_jid)
                        logger.debug(f"Participantes obtidos para broadcast: {len(jids)}")
                        await self.ensure_sessions_and_send_to_group(message_node, jids)
                        return
                    else:
                        logger.warning("Store não tem método findParticipantsByBcid, enviando sem participantes")
                        await self.ensure_sessions_and_send_to_group(message_node, [])
                        return
                except Exception as e:
                    logger.error(f"Erro ao obter participantes para broadcast: {e}")
                    await self.ensure_sessions_and_send_to_group(message_node, [])
                    return
            
            # Grupo normal (@g.us)
            # Cria sender key
            await self.axolotl_manager.group_create_skmsg(group_jid)
            
            # Obtém participantes do grupo
            if self.group_handler:
                try:
                    participants = await self.group_handler.get_group_participants(group_jid, own_jid=own_jid)
                    logger.debug(f"Participantes obtidos: {len(participants)}")
                    
                    # Garante sessões e envia
                    await self.ensure_sessions_and_send_to_group(message_node, participants)
                    return
                except Exception as e:
                    logger.error(f"Erro ao obter participantes do grupo via group_handler: {e}")
                    # Fallback: tenta IQ request direto
                    logger.debug("Tentando obter participantes via IQ request como fallback...")
                    try:
                        participants = await self._get_group_participants_via_iq(group_jid, own_jid)
                        logger.debug(f"Participantes obtidos via IQ: {len(participants)}")
                        await self.ensure_sessions_and_send_to_group(message_node, participants)
                        return
                    except Exception as iq_error:
                        logger.error(f"Erro ao obter participantes via IQ request: {iq_error}")
                        # Fallback final: envia sem distribution
                    await self._send_to_group_with_sessions(message_node, [], retry_count=0)
                    return
            else:
                logger.warning("GroupHandler não disponível, tentando IQ request direto...")
                try:
                    participants = await self._get_group_participants_via_iq(group_jid, own_jid)
                    logger.debug(f"Participantes obtidos via IQ: {len(participants)}")
                    await self.ensure_sessions_and_send_to_group(message_node, participants)
                    return
                except Exception as iq_error:
                    logger.error(f"Erro ao obter participantes via IQ request: {iq_error}")
                    # Fallback final: envia sem distribution
                await self._send_to_group_with_sessions(message_node, [], retry_count=0)
                return
        else:
            # Sender key existe, verifica retry
            logger.debug("Sender key encontrado, verificando retry...")
            
            retry_count = 0
            jids_need_sender_key = []
            
            if retry_receipt_entity is not None:
                # Extrai informações do retry
                # Tenta usar métodos se disponíveis (compatibilidade com objetos)
                if hasattr(retry_receipt_entity, 'getRetryCount'):
                    try:
                        retry_count = retry_receipt_entity.getRetryCount()
                    except Exception:
                        retry_count = 0
                else:
                    retry_count_attr = retry_receipt_entity.get_attribute("count")
                    if retry_count_attr:
                        try:
                            retry_count = int(retry_count_attr)
                        except (ValueError, TypeError):
                            retry_count = 0
                    
                    if hasattr(retry_receipt_entity, 'getRetryJid'):
                        try:
                            retry_jid = retry_receipt_entity.getRetryJid()
                            if retry_jid:
                                jids_need_sender_key = [retry_jid]
                                logger.debug(f"Retry detectado (via método): count={retry_count}, jid={retry_jid}")
                        except Exception:
                            pass
                    else:
                        retry_jid_attr = retry_receipt_entity.get_attribute("retry_jid")
                    if retry_jid_attr:
                        jids_need_sender_key = [retry_jid_attr]
                        logger.debug(f"Retry detectado (via atributo): count={retry_count}, jid={retry_jid_attr}")
                
            # Envia com sender key distribution se necessário
            await self._send_to_group_with_sessions(message_node, jids_need_sender_key, retry_count=retry_count)
    
    async def _get_group_participants_via_iq(
        self,
        group_jid: str,
        own_jid: Optional[str] = None
    ) -> List[str]:
        """
        Obtém participantes do grupo via IQ request direto (fallback).
        
        Usado quando group_handler.get_group_participants() falha.
        
        Args:
            group_jid: JID do grupo
            own_jid: JID próprio para remover da lista (opcional)
        
        Returns:
            Lista de JIDs dos participantes (sem o próprio JID)
        
        Raises:
            Exception: Se obtenção falhar
        """
        from .builders.group_builder import GroupBuilder
        
        if not self._iq_response_processor:
            raise RuntimeError("IQResponseProcessor não disponível")
        
        logger.debug(f"Obtendo participantes via IQ request para grupo: {group_jid}")
        
        # Constrói IQ request
        iq_node = GroupBuilder.build_get_info(group_jid)
        iq_id = iq_node.get_attribute("id")
        
        # Cria Future para aguardar resposta
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de informações do grupo"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao obter informações: tipo={node.get_attribute('type')}"))
                    return
                
                # Extrai informações do node <group>
                group_node = node.get_child("group")
                if not group_node:
                    future.set_exception(Exception("Resposta sem node <group>"))
                    return
                
                participants = []
                
                # Verifica addressing_mode para determinar qual atributo usar
                addressing_mode = group_node.get_attribute("addressing_mode")
                value_name = "phone_number" if addressing_mode == "lid" else "jid"
                
                # Extrai participantes
                for child in group_node.children:
                    if child.tag == "participant":
                        participant_id = child.get_attribute(value_name)
                        if participant_id:
                            participants.append(participant_id)
                
                # Remove próprio JID se estiver na lista
                if own_jid and own_jid in participants:
                    participants.remove(own_jid)
                
                logger.debug(f"Participantes obtidos via IQ: {len(participants)}")
                future.set_result(participants)
            
            except Exception as e:
                future.set_exception(e)
        
        # Registra callback
        self._iq_response_processor.register_callback(iq_id, on_response, timeout=30.0)
        
        # Envia IQ
        async def send_iq_fn(iq_node: ProtocolNode):
            await self._send_protocol_node(iq_node)
        
        await send_iq_fn(iq_node)
        
        # Aguarda resposta
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_response_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando informações do grupo via IQ")
    
    async def _send_to_group_with_sessions(
        self,
        message_node: ProtocolNode,
        jids_need_sender_key: Optional[List[str]] = None,
        retry_count: int = 0
    ) -> None:
        """
        Envia mensagem para grupo com sender key distribution para participantes.
        
        Baseado em AxolotlSendLayer.sendToGroupWithSessions() do zowsuplib.
        
        Args:
            message_node: ProtocolNode da mensagem (com <proto>)
            jids_need_sender_key: Lista de JIDs que precisam receber sender key distribution
            retry_count: Contador de retry (se > 0, é retry para participante específico)
        """
        group_jid = message_node.get_attribute("to")
        
        # CORREÇÃO: Normaliza group_jid para garantir que seja @g.us
        # O atributo 'to' deve sempre ser o JID do grupo, não do participante
        if not group_jid or not group_jid.endswith("@g.us") or len(group_jid) >= 15:
            # Se não termina com @g.us, pode ser que o to esteja incorreto
            # Tenta extrair o ID do grupo ou usar o to original
            # Se o to for um JID individual, isso é um erro - mas vamos tentar corrigir
            if group_jid and ("@s.whatsapp.net" in group_jid or "@lid" in group_jid):
                # Extrai o ID numérico antes do @
                group_id = group_jid.split("@")[0]
                group_jid = f"{group_id}@g.us"
                logger.warning(f"Corrigindo 'to' de {message_node.get_attribute('to')} para {group_jid}")
            
            # Atualiza o atributo 'to' do message_node
            if group_jid:
                message_node.attributes["to"] = group_jid
        
        proto_node = message_node.get_child("proto")
        if not proto_node:
            raise ValueError("Node de mensagem deve ter <proto>")
        
        proto_bytes = proto_node.data
        mediatype = proto_node.get_attribute("mediatype") if proto_node else "text"
        
        jids_need_sender_key = jids_need_sender_key or []
        enc_entities = []
        participant = jids_need_sender_key[0] if len(jids_need_sender_key) == 1 and retry_count > 0 else None
        
        # Para cada participante que precisa de sender key
        if len(jids_need_sender_key) > 0:
            # Cria sender key distribution message uma vez
            sender_key_distribution_message = await self.axolotl_manager.group_create_skmsg(group_jid)
            
            # Serializa para protobuf
            from ..proto.e2e_pb2 import Message as MessagePb
            distribution_pb = MessagePb()
            distribution_pb.sender_key_distribution_message.group_id = group_jid
            distribution_pb.sender_key_distribution_message.axolotl_sender_key_distribution_message = sender_key_distribution_message.serialize()
            
            # Se retry, mescla com mensagem original
            if retry_count > 0:
                distribution_pb.MergeFromString(proto_bytes)
            
            distribution_bytes = distribution_pb.SerializeToString()
            
            # Para cada JID, criptografa e cria <enc>
            for jid in jids_need_sender_key:
                recipient_id = jid.split('@')[0]
                
                # Criptografa com sessão do participante
                ciphertext = await self.axolotl_manager.encrypt(recipient_id, distribution_bytes)
                
                # Identifica tipo
                if isinstance(ciphertext, PreKeyWhisperMessage):
                    enc_type = EncEntity.TYPE_PKMSG
                elif isinstance(ciphertext, WhisperMessage):
                    enc_type = EncEntity.TYPE_MSG
                else:
                    enc_type = EncEntity.TYPE_MSG
                
                # Cria <enc> com jid (ou participant se retry)
                enc_node = EncEntity.create_enc_node(
                    enc_type=enc_type,
                    ciphertext=ciphertext.serialize(),
                    mediatype=mediatype,
                    jid=None if participant else jid,  # Se participant, jid=None e usa participant no message
                    count=str(retry_count) if retry_count > 0 else None
                )
                
                enc_entities.append(enc_node)
        
        # CORREÇÃO: SKMSG deve ser sempre adicionado, não apenas quando retry_count == 0
        # O SKMSG é a mensagem principal criptografada com sender key que todos os participantes precisam receber
        # Mesmo que não haja participantes que precisam de sender key distribution, o SKMSG ainda é necessário
        try:
            # Criptografa mensagem original com sender key
            ciphertext = await self.axolotl_manager.group_encrypt(group_jid, proto_bytes)
            
            skmsg_node = EncEntity.create_enc_node(
                enc_type=EncEntity.TYPE_SKMSG,
                ciphertext=ciphertext,
                mediatype=mediatype,
                jid=None
            )
            
            enc_entities.append(skmsg_node)
                
        except exceptions.NoSessionException as e:
        # Se sender key não existe, criar antes
            logger.warning(f"Sender key não encontrado para grupo {group_jid}, criando...")
            await self.axolotl_manager.group_create_skmsg(group_jid)
            # Tentar criptografar novamente
            ciphertext = await self.axolotl_manager.group_encrypt(group_jid, proto_bytes)
            
            skmsg_node = EncEntity.create_enc_node(
                enc_type=EncEntity.TYPE_SKMSG,
                ciphertext=ciphertext,
                mediatype=mediatype,
                jid=None
            )
            
            enc_entities.append(skmsg_node)
        except Exception as e:
            # Em caso de erro, loga mas não falha completamente
            # O SKMSG é crítico, mas em retries pode ser que a mensagem original já tenha sido enviada
            logger.warning(f"Erro ao criar SKMSG para grupo {group_jid}: {e}")
            # Tenta criar sender key e tentar novamente
            try:
                await self.axolotl_manager.group_create_skmsg(group_jid)
                ciphertext = await self.axolotl_manager.group_encrypt(group_jid, proto_bytes)
                skmsg_node = EncEntity.create_enc_node(
                    enc_type=EncEntity.TYPE_SKMSG,
                    ciphertext=ciphertext,
                    mediatype=mediatype,
                    jid=None
                )
                enc_entities.append(skmsg_node)
            except Exception as e2:
                logger.error(f"Erro crítico ao criar SKMSG após tentativa de criar sender key: {e2}")
                # Não adiciona SKMSG, mas continua - pode ser um retry onde o SKMSG já foi enviado
        
        # Constrói node final usando EncryptedMessageBuilder
        message_node = EncryptedMessageBuilder.build_encrypted_message(
            message_node=message_node,
            enc_entities=enc_entities,
            participant=participant
        )
        
        # Obtém tctoken se necessário (para grupos, pode não ser necessário, mas verificamos)
        tctoken = None
        if hasattr(self, 'axolotl_manager') and hasattr(self.axolotl_manager, '_store'):
            # Para grupos, tctoken geralmente não é usado, mas verificamos se houver participant específico
            if participant:
                tctoken = await self.axolotl_manager._store.getTcToken(participant)
            else:
                # Verifica se há algum JID individual na lista que precisa de tctoken
                # (geralmente grupos não usam tctoken, mas mantemos compatibilidade)
                pass
        
        # Adiciona elementos extras
        await self._add_message_extras(message_node, tctoken=tctoken)
        
        # Enfileira mensagem antes de enviar (para retry)
        self._enqueue_sent_message(message_node)
        
        # Envia
        await self._send_protocol_node(message_node)
    
    async def ensure_sessions_and_send_to_group(
        self,
        message_node: ProtocolNode,
        jids: List[str]
    ) -> None:
        """
        Garante que há sessões para os JIDs e envia mensagem para grupo.
        
        Baseado em AxolotlSendLayer.ensureSessionsAndSendToGroup() do zowsuplib.
        
        Args:
            message_node: ProtocolNode da mensagem (com <proto>)
            jids: Lista de JIDs dos participantes
        """
        logger.debug(f"ensure_sessions_and_send_to_group: {len(jids)} JIDs")
        
        # Normaliza JIDs (remove .0:0, .1:)
        standard_jids = []
        for jid in jids:
            standard_jid = jid.replace(".0:0", "").replace(".1:", ":")
            standard_jids.append(standard_jid)
        
        # Separa JIDs com sessão dos sem sessão
        all_jids = []
        jids_no_session = []
        
        for jid in standard_jids:
            recipient_id = jid.split('@')[0]
            if await self.axolotl_manager.session_exists(recipient_id):
                all_jids.append(jid)
            else:
                jids_no_session.append(jid)
        
        async def on_get_keys_success(success_jids: List[str], errors: Dict[str, Exception]):
            """Callback quando chaves são obtidas"""
            if len(errors) > 0:
                # Processa erros (pode logar ou tratar)
                for jid, error in errors.items():
                    logger.warning(f"Erro ao obter chaves para {jid}: {error}")
            
            # Adiciona JIDs com sucesso
            all_jids.extend(success_jids)
            
            # Envia para grupo com todos os JIDs
            await self._send_to_group_with_sessions(message_node, all_jids, retry_count=0)
        
        # Se há JIDs sem sessão, obtém chaves primeiro
        if len(jids_no_session) > 0:
            # Obtém chaves para JIDs sem sessão
            success_jids, error_jids = await self._get_keys_for_jids(jids_no_session)
            await on_get_keys_success(success_jids, error_jids)
        else:
            # Todos têm sessão, envia direto
            await self._send_to_group_with_sessions(message_node, standard_jids, retry_count=0)
    
    async def _add_message_extras(
        self, 
        message_node: ProtocolNode, 
        tctoken: Optional[bytes] = None
    ) -> None:
        """
        Adiciona elementos extras à mensagem (reporting, device-identity, tctoken, biz, etc.).
        
        Baseado em AxolotlSendLayer.sendEncEntities()
        Ordem: reporting → tctoken → biz → device-identity
        """
        import os
        import base64
        
        # Adiciona reporting token (se não for peer message)
        # Baseado em AxolotlSendLayer.sendEncEntities() linha 184-191
        category = message_node.get_attribute("category")
        if category != "peer":
            reporting = ProtocolNode(
                tag="reporting",
                attributes={},
                children=[]
            )
            reporting_token = ProtocolNode(
                tag="reporting_token",
                attributes={"v": "2"},
                data=os.urandom(16)
            )
            reporting.children.append(reporting_token)
            message_node.children.append(reporting)
        
        # Adiciona tctoken se fornecido (para trusted contacts)
        # Baseado em AxolotlSendLayer.sendEncEntities() linha 193-195
        if tctoken:
            tctoken_node = ProtocolNode(
                tag="tctoken",
                attributes={},
                data=tctoken
            )
            message_node.children.append(tctoken_node)
        
        # Adiciona biz node se presente (já foi copiado pelo EncryptedMessageBuilder)
        # Baseado em AxolotlSendLayer.sendEncEntities() linha 197-199
        # O biz node já está no message_node.children se existir
        
        # Adiciona device-identity se houver
        # Baseado em AxolotlSendLayer.sendEncEntities() linha 201-205
        if self.profile and self.config:
            if hasattr(self.config, 'device_identity') and self.config.device_identity:
                try:
                    did_data = base64.b64decode(self.config.device_identity)
                    device_identity = ProtocolNode(
                        tag="device-identity",
                        attributes={},
                        data=did_data
                    )
                    message_node.children.append(device_identity)
                except Exception as e:
                    logger.warning(f"Erro ao adicionar device-identity: {e}")
    

    
    async def start_typing(self, to: str) -> None:
        """
        Envia indicador de "digitando" para um contato.
        
        Args:
            to: JID do destinatário
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        from ..protocol.entities import PresenceProtocolEntity
        
        # Normaliza JID
        to_jid = to_whatsapp_jid(to)
        
        # Cria presence de typing
        presence = PresenceProtocolEntity(
            presence_type=PresenceProtocolEntity.TYPE_COMPOSING,
            to=to_jid
        )
        
        logger.debug(f"Enviando indicador de typing para {to_jid}")
        await self._send_protocol_node(presence)
    
    async def stop_typing(self, to: str) -> None:
        """
        Para o indicador de "digitando" para um contato.
        
        Args:
            to: JID do destinatário
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        from ..protocol.entities import PresenceProtocolEntity
        
        # Normaliza JID
        to_jid = to_whatsapp_jid(to)
        
        # Cria presence de paused
        presence = PresenceProtocolEntity(
            presence_type=PresenceProtocolEntity.TYPE_PAUSED,
            to=to_jid
        )
        
        logger.debug(f"Parando indicador de typing para {to_jid}")
        await self._send_protocol_node(presence)
    
    def is_connected(self) -> bool:
        """Verifica se está conectado e autenticado"""
        return self._connected and self._authenticated
    
    async def disconnect(self) -> None:
        """
        Desconecta completamente e finaliza todos os recursos da instância.
        
        Finaliza todas as tasks, limpa filas, cancela futures pendentes
        e desconecta todos os componentes de forma limpa.
        """
        logger.info("Desconectando e finalizando todos os recursos...")
        
        self._running = False
        self._connected = False
        self._authenticated = False
        
        # 1. Cancela futures pendentes (evita deadlocks)
        async def _cancel_pending_futures() -> None:
            async with self._pending_keys_lock:
                for jid, fut in list(self._pending_keys_requests.items()):
                    if not fut.done():
                        fut.cancel()
                        try:
                            await fut
                        except (asyncio.CancelledError, Exception):
                            pass
                self._pending_keys_requests.clear()
            async with self._pending_pkmsg_sync_lock:
                for jid, fut in list(self._pending_pkmsg_sync_requests.items()):
                    if not fut.done():
                        fut.cancel()
                        try:
                            await fut
                        except (asyncio.CancelledError, Exception):
                            pass
                self._pending_pkmsg_sync_requests.clear()
        
        try:
            await _cancel_pending_futures()
        except Exception as e:
            logger.warning(f"Erro ao cancelar futures pendentes: {e}")
        
        # 2. Para bridge
        if self.bridge:
            try:
                await self.bridge.stop()
            except Exception as e:
                logger.warning(f"Erro ao parar bridge: {e}")
        
        # 3. Cancela stream
        if self.stream:
            try:
                await self.stream.cancel()
            except Exception as e:
                logger.warning(f"Erro ao cancelar stream: {e}")
        
        # 4. Cancela tasks principais
        tasks = []
        if self._message_loop_task:
            tasks.append(self._message_loop_task)
        if self._keepalive_task:
            tasks.append(self._keepalive_task)
        if self._bridge_task:
            tasks.append(self._bridge_task)
        for task in tasks:
            if task and not task.done():
                task.cancel()
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"Erro ao aguardar cancelamento de tasks: {e}")
    
        # 5. Finaliza IQResponseProcessor (cleanup task + callbacks)
        if self._iq_response_processor:
            try:
                await self._iq_response_processor.shutdown()
            except Exception as e:
                logger.warning(f"Erro ao finalizar IQResponseProcessor: {e}")
        
        # 6. Limpa filas e recursos
        self._sent_messages_queue.clear()
        self._pending_messages.clear()
        self._unsent_prekeys.clear()
        self._pending_keys_retry = None
        self._last_sync_time.clear()
        self._last_message_time.clear()
        self._daily_message_count = 0
        
        # 7. Desconecta TCP
        if self.connection:
            try:
                await self.connection.disconnect()
            except Exception as e:
                logger.warning(f"Erro ao desconectar TCP: {e}")
        
        # 8. Limpa referências de tasks
        self._message_loop_task = None
        self._keepalive_task = None
        self._bridge_task = None
        
        # 9. Emite evento de desconexão
        try:
            await self.events.emit("disconnected", {"account_id": self.account_id})
        except Exception as e:
            logger.warning(f"Erro ao emitir evento de desconexão: {e}")
        
        # 10. Finaliza emitter (encerra executor e evita threads órfãs)
        try:
            self.events.shutdown()
        except Exception as e:
            logger.warning(f"Erro ao finalizar events: {e}")
        
        # 11. Finaliza conexões do engine (fecha pool de conexões do banco)
        # Nota: O engine é compartilhado globalmente. Fechar o pool aqui garante
        # que não há conexões órfãs. Se houver outros clients ativos, eles
        # recriarão conexões automaticamente quando necessário.
        try:
            from zowpy.db.config.engine import engine
            await engine.dispose(close=True)
            logger.debug("Engine do banco de dados finalizado")
        except Exception as e:
            logger.warning(f"Erro ao finalizar engine: {e}")
        
        logger.info("Desconectado e todos os recursos finalizados")
    
    async def reconnect(self) -> None:
        """
        Reconecta ao WhatsApp.
        
        Desconecta completamente e reconecta usando o mesmo account_id e configurações.
        Útil após envio de prekeys ou outros eventos que requerem reconexão.
        """
        logger.info("Reconectando...")
        
        # Desconecta completamente
        await self.disconnect()
        
        # Aguarda um pouco para garantir que tudo foi limpo
        await asyncio.sleep(0.5)
        
        # Reconecta
        await self.connect()
        
        logger.info("Reconectado com sucesso")
    
    async def _check_and_flush_prekeys(self, prekeys_generated: list=[]) -> None:
        """
        Verifica e envia prekeys não enviadas.
        
        Baseado em AxolotlControlLayer.onAuthed()
        """

        try:
            # Carrega prekeys não enviadas
            unsent_prekeys_result = prekeys_generated or await self.axolotl_manager.load_unsent_prekeys()
            logger.debug(f"load_unsent_prekeys retornou tipo: {type(unsent_prekeys_result)}")
            
            # Garante que é uma lista
            if unsent_prekeys_result is None:
                self._unsent_prekeys = []
            elif isinstance(unsent_prekeys_result, list):
                self._unsent_prekeys = unsent_prekeys_result



            if len(self._unsent_prekeys) > 0:
                logger.info(f"Encontradas {len(self._unsent_prekeys)} prekeys não enviadas, enviando...")
                signed_prekey = await self.axolotl_manager.load_latest_signed_prekey(generate=True)
                if signed_prekey:
                    await self._flush_prekeys(signed_prekey, self._unsent_prekeys[:], reboot_connection=True)
                    self._unsent_prekeys = []
                else:
                    logger.warning("Não foi possível gerar signed_prekey, não é possível enviar prekeys")
            else:
                logger.debug("Nenhuma prekey não enviada encontrada")
        except Exception as e:
            logger.exception(e)
            logger.error(f"Erro ao verificar/enviar prekeys: {e}", exc_info=True)
    
    async def _flush_prekeys(
        self,
        signed_prekey,
        prekeys: List,
        reboot_connection: bool = False,
        retry_count: int = 0
    ) -> None:
        """
        Envia prekeys para o servidor.
        
        Baseado em AxolotlControlLayer.flush_keys()
        
        Args:
            signed_prekey: SignedPreKeyRecord
            prekeys: Lista de PreKeyRecord
            reboot_connection: Se deve reiniciar conexão após enviar
            retry_count: Contador de retry (para retry automático)
        """
        import random
        import binascii
        
        logger.info("=" * 80)
        logger.info("[ZOWPY] _flush_prekeys() INICIADO")
        logger.info(f"[ZOWPY] Parâmetros: prekeys_count={len(prekeys)}, reboot_connection={reboot_connection}, retry_count={retry_count}")
        
        # Armazena informações para retry se necessário
        async with self._keys_retry_lock:
            self._pending_keys_retry = (signed_prekey, prekeys, reboot_connection, retry_count)
        
        # Prepara dicionário de prekeys
        logger.info("[ZOWPY] Preparando prekeys_dict...")
        prekeys_dict = {}
        for i, prekey in enumerate(prekeys):
            key_pair = prekey.getKeyPair()
            prekey_id_orig = prekey.getId()
            logger.debug(f"[ZOWPY] Prekey[{i}] ID={prekey_id_orig}, public_key serialized len={len(key_pair.getPublicKey().serialize())}")
            
            # Serializa public key (remove primeiro byte)
            public_key_bytes = key_pair.getPublicKey().serialize()[1:]
            logger.debug(f"[ZOWPY] Prekey[{i}] public_key after [1:] len={len(public_key_bytes)}")
            
            # Ajusta array e ID (como no zowsuplib)
            adjusted_id = PrekeyBuilder._adjust_id(prekey_id_orig)
            adjusted_key = PrekeyBuilder._adjust_array(public_key_bytes)
            prekeys_dict[adjusted_id] = adjusted_key
            
            logger.debug(f"[ZOWPY] Prekey[{i}] ID ajustado: {prekey_id_orig} (int) -> {len(adjusted_id)} bytes: {binascii.hexlify(adjusted_id).decode()}")
            logger.debug(f"[ZOWPY] Prekey[{i}] Key ajustado: raw_len={len(public_key_bytes)}, adjusted_len={len(adjusted_key)}, first_20_hex={binascii.hexlify(adjusted_key[:20]).decode() if len(adjusted_key) >= 20 else binascii.hexlify(adjusted_key).decode()}")
            
            # Log detalhado para os primeiros 3 prekeys
            if i < 3:
                logger.info(f"[ZOWPY] Prekey[{i}] FINAL: id_hex={binascii.hexlify(adjusted_id).decode()}, key_first_40_hex={binascii.hexlify(adjusted_key[:40]).decode() if len(adjusted_key) >= 40 else binascii.hexlify(adjusted_key).decode()}...")
        
        logger.info(f"[ZOWPY] preKeysDict criado com {len(prekeys_dict)} prekeys")
        
        # Prepara signed prekey
        logger.info("[ZOWPY] Preparando signedKeyTuple...")
        signed_prekey_id = signed_prekey.getId()
        logger.info(f"[ZOWPY] Signed prekey ID original: {signed_prekey_id} (int, tipo={type(signed_prekey_id)})")
        
        # Ajusta signed prekey ID
        adjusted_signed_id = PrekeyBuilder._adjust_id(signed_prekey_id)
        logger.info(f"[ZOWPY] Signed prekey ID ajustado: {len(adjusted_signed_id)} bytes: {binascii.hexlify(adjusted_signed_id).decode()}")
        
        # Serializa signed prekey public key
        signed_public_key_serialized = signed_prekey.getKeyPair().getPublicKey().serialize()
        logger.debug(f"[ZOWPY] Signed prekey public_key serialized len={len(signed_public_key_serialized)}")
        signed_public_key_trimmed = signed_public_key_serialized[1:]
        logger.debug(f"[ZOWPY] Signed prekey public_key after [1:] len={len(signed_public_key_trimmed)}")
        
        # Ajusta signed prekey public key
        adjusted_signed_key = PrekeyBuilder._adjust_array(signed_public_key_trimmed)
        logger.info(f"[ZOWPY] Signed prekey key ajustado: raw_len={len(signed_public_key_trimmed)}, adjusted_len={len(adjusted_signed_key)}, first_40_hex={binascii.hexlify(adjusted_signed_key[:40]).decode() if len(adjusted_signed_key) >= 40 else binascii.hexlify(adjusted_signed_key).decode()}...")
        
        # Serializa signature
        signature_raw = signed_prekey.getSignature()
        logger.debug(f"[ZOWPY] Signed prekey signature raw len={len(signature_raw)}, first_40_hex={binascii.hexlify(signature_raw[:40]).decode() if len(signature_raw) >= 40 else binascii.hexlify(signature_raw).decode()}...")
        
        # Ajusta signature
        adjusted_signature = PrekeyBuilder._adjust_array(signature_raw)
        logger.info(f"[ZOWPY] Signed prekey signature ajustado: raw_len={len(signature_raw)}, adjusted_len={len(adjusted_signature)}, first_40_hex={binascii.hexlify(adjusted_signature[:40]).decode() if len(adjusted_signature) >= 40 else binascii.hexlify(adjusted_signature).decode()}...")
        
        signed_key_tuple = (adjusted_signed_id, adjusted_signed_key, adjusted_signature)
        logger.info(f"[ZOWPY] signedKeyTuple criado: id_len={len(adjusted_signed_id)}, key_len={len(adjusted_signed_key)}, sig_len={len(adjusted_signature)}")
        
        # Prepara identity key
        logger.info("[ZOWPY] Preparando identity key...")
        identity_public_key_serialized = self.axolotl_manager.identity.getPublicKey().serialize()
        logger.debug(f"[ZOWPY] Identity public_key serialized len={len(identity_public_key_serialized)}")
        identity_public_key_trimmed = identity_public_key_serialized[1:]
        logger.debug(f"[ZOWPY] Identity public_key after [1:] len={len(identity_public_key_trimmed)}")
        
        adjusted_identity = PrekeyBuilder._adjust_array(identity_public_key_trimmed)
        logger.info(f"[ZOWPY] Identity key ajustado: raw_len={len(identity_public_key_trimmed)}, adjusted_len={len(adjusted_identity)}, first_40_hex={binascii.hexlify(adjusted_identity[:40]).decode() if len(adjusted_identity) >= 40 else binascii.hexlify(adjusted_identity).decode()}...")
        
        # Prepara registration ID
        logger.info("[ZOWPY] Preparando registration_id...")
        registration_id_int = self.axolotl_manager.registration_id
        logger.info(f"[ZOWPY] Registration ID original: {registration_id_int} (int, tipo={type(registration_id_int)})")
        
        adjusted_registration_id = PrekeyBuilder._adjust_id(registration_id_int, byte_count=4)
        logger.info(f"[ZOWPY] Registration ID ajustado: {len(adjusted_registration_id)} bytes: {binascii.hexlify(adjusted_registration_id).decode()}")
        
        # Cria IQ node
        logger.info("[ZOWPY] Criando SetKeysIqProtocolEntity...")
        logger.info("[ZOWPY] Parâmetros do SetKeysIqProtocolEntity:")
        logger.info(f"[ZOWPY]   - identityKey: {len(adjusted_identity)} bytes")
        logger.info(f"[ZOWPY]   - signedPreKey: tuple({len(adjusted_signed_id)}, {len(adjusted_signed_key)}, {len(adjusted_signature)})")
        logger.info(f"[ZOWPY]   - preKeys: dict com {len(prekeys_dict)} chaves")
        logger.info(f"[ZOWPY]   - djbType: 5")
        logger.info(f"[ZOWPY]   - registrationId: {len(adjusted_registration_id)} bytes")
        
        iq_node = PrekeyBuilder.build_set_keys_iq(
            identity_key=adjusted_identity,
            signed_prekey=signed_key_tuple,
            prekeys=prekeys_dict,
            registration_id=adjusted_registration_id,
            djb_type=5,
            iq_id=None
        )
        
        iq_id = iq_node.get_attribute("id")
        logger.info(f"[ZOWPY] IQ node criado, ID: {iq_id}")
   
        async def on_error(node: ProtocolNode):
            """Callback de erro"""
            logger.info(f"Callback flush keys de erro: {node}")
            await self._on_sent_keys_error(node, iq_node, signed_prekey, prekeys, reboot_connection, retry_count)

        async def on_success(node):
            await self._on_keys_flushed(prekeys, reboot_connection=reboot_connection)

        # Registra callbacks e envia
        self._iq_response_processor.register_callback(iq_id, on_success, timeout=30.0)

        await self._send_protocol_node(iq_node)
        
        logger.info(f"[ZOWPY] Enviando IQ node para servidor...")
        logger.info(f"[ZOWPY] Prekeys enviadas: {len(prekeys)} prekeys, signed_prekey_id={signed_prekey.getId()}")
        logger.info("[ZOWPY] _flush_prekeys() FINALIZADO")
        logger.info("=" * 80)
    
    async def _on_keys_flushed(self, prekeys: list, reboot_connection: bool = False) -> None:
        """
        Callback quando prekeys são enviadas com sucesso.
        
        Baseado em AxolotlControlLayer.on_keys_flushed()
        """
        logger.info("=" * 80)
        logger.info("[ZOWPY] _on_keys_flushed() - Prekeys enviadas com sucesso!")
        logger.info(f"[ZOWPY] Prekeys enviadas: {len(prekeys)}")
        
        async with self._keys_retry_lock:
            self._pending_keys_retry = None
        
        await self.axolotl_manager.set_prekeys_as_sent(prekeys)
        
        logger.info(f"[ZOWPY] Prekeys marcadas como enviadas: {len(prekeys)} prekeys")
        
        # if reboot_connection:
        #     logger.info("[ZOWPY] Reiniciando conexão após envio de prekeys...")
        #     await self.reconnect()
        
        logger.info("[ZOWPY] _on_keys_flushed() FINALIZADO")
        logger.info("=" * 80)
    
    async def _on_sent_keys_error(
        self,
        error_node: ProtocolNode,
        original_iq: ProtocolNode,
        signed_prekey,
        prekeys: List,
        reboot_connection: bool,
        retry_count: int
    ) -> None:
        """
        Trata erros ao enviar prekeys.
        
        Baseado em AxolotlControlLayer.onSentKeysError()
        """
        import random
        
        # Extrai informações do erro
        error_child = error_node.get_child("error")
        if error_child:
            error_code = error_child.get_attribute("code")
            error_text = error_child.get_attribute("text")
            backoff = error_child.get_attribute("backoff")
            
            logger.warning(f"Erro ao enviar prekeys: code={error_code}, text={error_text}, backoff={backoff}")
            
            # Se for erro 503 (service-unavailable), tenta retry com backoff
            if error_code == "503":
                async with self._keys_retry_lock:
                    if self._pending_keys_retry is None:
                        logger.warning("Erro 503 ao enviar prekeys, mas não há informações de retry disponíveis.")
                        return
                    
                    retry_count += 1
                    
                    if retry_count >= 5:  # Máximo de 5 tentativas
                        logger.error(f"Falha ao enviar prekeys após {retry_count} tentativas. Desistindo.")
                        self._pending_keys_retry = None
                        return
                    
                    # Calcula backoff exponencial com jitter
                    backoff_seconds = min(2 ** retry_count + random.uniform(0, 1), 60)  # Máximo 60 segundos
                    logger.info(f"Erro 503 ao enviar prekeys. Agendando retry {retry_count}/5 em {backoff_seconds:.1f} segundos...")
                    
                    # Atualiza o contador de retry
                    self._pending_keys_retry = (signed_prekey, prekeys, reboot_connection, retry_count)
                    
                    # Agenda retry
                    await asyncio.sleep(backoff_seconds)
                    
                    # Verifica se ainda está pendente
                    async with self._keys_retry_lock:
                        if self._pending_keys_retry:
                            logger.info(f"Tentando reenviar prekeys (tentativa {retry_count + 1}/5)...")
                            await self._flush_prekeys(signed_prekey, prekeys, reboot_connection=reboot_connection, retry_count=retry_count)
            else:
                # Outros erros (não 503)
                logger.error(f"Erro ao enviar prekeys: code={error_code}, text={error_text}. Não será feito retry automático.")
                async with self._keys_retry_lock:
                    self._pending_keys_retry = None
        else:
            logger.warning("Erro ao enviar prekeys, mas não foi possível extrair informações do erro")
            async with self._keys_retry_lock:
                self._pending_keys_retry = None
    
    def _enqueue_sent_message(self, node: ProtocolNode) -> None:
        """
        Adiciona mensagem à fila de mensagens enviadas.
        
        Baseado em AxolotlSendLayer.enqueueSent()
        
        Args:
            node: Protocol node da mensagem enviada
        """
        if len(self._sent_messages_queue) >= self._MAX_SENT_QUEUE:
            logger.warning("Fila de mensagens enviadas cheia, removendo mensagem mais antiga")
            self._sent_messages_queue.pop(0)
        
        self._sent_messages_queue.append(node)
        logger.debug(f"Mensagem enfileirada: id={node.get_attribute('id')}")
    
    async def _get_enqueued_message(
        self,
        message_id: str,
        keep_enqueued: bool = False
    ) -> Optional[ProtocolNode]:
        """
        Busca mensagem na fila de mensagens enviadas.
        
        Baseado em AxolotlSendLayer.getEnqueuedMessageNode()
        
        Args:
            message_id: ID da mensagem
            keep_enqueued: Se True, não remove da fila
        
        Returns:
            ProtocolNode da mensagem ou None se não encontrada
        """
        for i in range(len(self._sent_messages_queue)):
            if self._sent_messages_queue[i].get_attribute("id") == message_id:
                if keep_enqueued:
                    return self._sent_messages_queue[i]
                return self._sent_messages_queue.pop(i)
        
        return None
    
    async def _resend_message_for_retry(
        self,
        message_node: ProtocolNode,
        retry_jid: Optional[str] = None,
        retry_count: int = 0
    ) -> None:
        """
        Re-envia mensagem para retry.
        
        Baseado em AxolotlSendLayer.receive() para retry receipts.
        
        Args:
            message_node: ProtocolNode da mensagem original
            retry_jid: JID específico para retry (se None, usa do node)
            retry_count: Contador de retry
        """
        logger.info(f"Re-enviando mensagem para retry: id={message_node.get_attribute('id')}, retry_jid={retry_jid}, retry_count={retry_count}")
        
        # Se retry_jid está especificado, obtém chaves para ele primeiro
        if retry_jid:
            recipient_id = retry_jid.split('@')[0]
            success_jids, error_jids = await self._get_keys_for_recipient(recipient_id, reason="retry")
            
            if error_jids:
                logger.warning(f"Erros ao obter chaves para retry: {error_jids}")
            
            if success_jids:
                # Tem sessão agora, re-envia
                await self.ensure_sessions_and_send_to_contacts(message_node, success_jids, retry_count=retry_count)
            else:
                logger.error(f"Não foi possível obter chaves para {retry_jid}, não é possível re-enviar")
        else:
            # Re-envia normalmente (sem JID específico)
            to_jid = message_node.get_attribute("to")
            if not to_jid:
                logger.error("Não é possível re-enviar: node não tem 'to'")
                return
            
            # Processa como mensagem normal
            await self.process_plaintext_node_and_send(message_node)
    
    async def _process_pending_messages(
        self,
        from_jid: str,
        participant_jid: Optional[str] = None,
        success_jids: Optional[List[str]] = None
    ) -> None:
        """
        Processa mensagens pendentes após obter sessão.
        
        Baseado em AxolotlReceiveLayer.processPendingIncomingMessages()
        
        Args:
            from_jid: JID do remetente
            participant_jid: JID do participante (para grupos, opcional)
        """
        conversation_id = (from_jid, participant_jid)
        
        if conversation_id not in self._encryption_receiver._pending_messages:
            logger.debug(f"Nenhuma mensagem pendente para {conversation_id}")
            return
        
        pending = self._encryption_receiver._pending_messages[conversation_id]
        logger.info(f"Processando {len(pending)} mensagens pendentes para {conversation_id}")
        
        # Processa cada mensagem pendente
        for message_node in pending:
            try:
                # Tenta descriptografar novamente
                decrypted_bytes = await self._encryption_receiver.decrypt_message(message_node)
                if decrypted_bytes:
                    # Processa mensagem descriptografada
                    await self._process_protocol_node(message_node, decrypted_bytes)
            except Exception as e:
                logger.error(f"Erro ao processar mensagem pendente: {e}", exc_info=True)
        
        # Remove mensagens processadas
        del self._encryption_receiver._pending_messages[conversation_id]
        logger.info(f"Mensagens pendentes processadas e removidas para {conversation_id}")
    
    async def _send_pkmsg_for_invalid_message(
        self,
        from_jid: str,
        message_id: str,
        participant: Optional[str] = None
    ) -> None:
        """
        Envia PKMSG para sincronização quando InvalidMessage após múltiplas tentativas.
        
        Baseado em AxolotlReceiveLayer.send_pkmsg_for_invalid_message() e 
        AxolotlSendLayer.sendToContactAsPkmsg() do zowsuplib.
        
        Envia uma mensagem vazia/minimal como PKMSG para forçar a criação de uma nova sessão
        e re-sincronização com o remetente. Deleta temporariamente a sessão existente para 
        forçar envio como PKMSG.
        
        Se já houver uma requisição em andamento para o mesmo JID, a nova requisição será ignorada.
        
        Args:
            from_jid: JID do remetente (pode ser grupo ou contato)
            message_id: ID da mensagem que falhou
            participant: Participante (para grupos, opcional)
        """
        future = None
        normalized_sender_jid = None
        
        try:
            from ..utils.tools import WATools

            sender_jid = participant if participant else from_jid
            
            # Normaliza JID se necessário (baseado em zowsuplib)
            normalized_sender_jid = WATools.normalizeJid(from_jid)
            
            # Verifica se já há uma requisição em andamento para este JID
            async with self._pending_pkmsg_sync_lock:
                if normalized_sender_jid in self._pending_pkmsg_sync_requests:
                    existing_future = self._pending_pkmsg_sync_requests[normalized_sender_jid]
                    if not existing_future.done():
                        logger.debug(f"PKMSG de sincronização já em andamento para {normalized_sender_jid}, ignorando nova requisição")
                        return
                    else:
                        # Future já concluída, remove da fila
                        del self._pending_pkmsg_sync_requests[normalized_sender_jid]
                
                # Cria nova Future para rastrear esta requisição
                future = asyncio.Future()
                self._pending_pkmsg_sync_requests[normalized_sender_jid] = future
            
            logger.info(f"Enviando PKMSG para sincronização com {normalized_sender_jid} (mensagem {message_id})")
            
            # Para grupos, envia para o grupo com participant
            to_jid = from_jid if participant else normalized_sender_jid
            
            # Cria mensagem de texto vazia
            # Baseado em zowsuplib: TextMessageProtocolEntity("", message_attrs)
            from ..proto.e2e_pb2 import Message as MessagePb
            message_pb = MessagePb()
            message_pb.conversation = ""  # Mensagem vazia
            
            # Serializa protobuf
            proto_bytes = message_pb.SerializeToString()
            
            # Gera ID para a mensagem de sincronização
            # Baseado em zowsuplib: f"sync_{message_id}_{int(time.time())}"
            sync_message_id = f"sync_{message_id}_{int(time.time())}"
            
            # Cria node de mensagem
            # Baseado em zowsuplib: TextMessageProtocolEntity.toProtocolTreeNode()
            message_node = ProtocolNode(
                tag="message",
                attributes={
                    "to": to_jid,
                    "type": "text",
                    "id": sync_message_id,
                    "t": str(int(time.time()))
                },
                children=[]
            )
            
            # Adiciona node <proto> com mediatype (seguindo padrão de _send_as_pkmsg)
            proto_node = ProtocolNode(
                tag="proto",
                attributes={"mediatype": "text"},
                data=proto_bytes
            )
            message_node.children.append(proto_node)
            
            # Para grupos, adiciona participant
            if participant:
                message_node.attributes["participant"] = normalized_sender_jid
            
            # Baseado em zowsuplib sendToContactAsPkmsg():
            # 1. Deleta temporariamente a sessão existente para forçar PKMSG
            # 2. Obtém chaves (PreKeys)
            # 3. Encripta como PreKeyWhisperMessage
            # 4. Restaura sessão se houver erro
            
            recipient_id = normalized_sender_jid.split('@')[0]
            
            # Backup e deleta sessão temporariamente (se existir) para forçar PKMSG
            # Baseado em zowsuplib: session_backup e deleteSession()
            session_backup = None
            had_session = False
            recipient_id_split = None
            deviceid = None
            
            if hasattr(self, 'axolotl_manager') and self.axolotl_manager:
                if await self.axolotl_manager.session_exists(normalized_sender_jid):
                    try:
                        # Decodifica JID para obter recipient_id e device_id
                        from ..utils.tools import WATools
                        recipient_id_split, _, deviceid = WATools.jidDecode(normalized_sender_jid)
                        
                        # Carrega sessão para backup
                        if hasattr(self.axolotl_manager, '_store'):
                            session_record = await self.axolotl_manager._store.loadSession(
                                recipient_id_split, 
                                deviceid
                            )
                            session_backup = session_record
                            had_session = True
                            logger.debug(f"Sessão existente encontrada para {normalized_sender_jid}, será deletada temporariamente")
                            
                            # Deleta sessão temporariamente para forçar PKMSG
                            await self.axolotl_manager._store.deleteSession(recipient_id_split, deviceid)
                            logger.debug(f"Sessão deletada temporariamente para {normalized_sender_jid}")
                    except Exception as e:
                        logger.warning(f"Erro ao fazer backup/deletar sessão: {e}")
            
            try:
                # Obtém chaves do remetente para atualizar sessão
                to_jid = normalized_sender_jid
                if "@" not in to_jid:
                    to_jid = f"{to_jid}@{YowConstants.WHATSAPP_SERVER}"

                success_jids, error_jids = await self._get_keys_for_recipient(to_jid, reason=None)
                
                if not success_jids:
                    logger.error(f"Erro ao obter chaves para sincronização: {error_jids}")
                    # Restaura sessão se houver backup
                    if had_session and session_backup and recipient_id_split is not None and deviceid is not None:
                        try:
                            await self.axolotl_manager._store.storeSession(recipient_id_split, deviceid, session_backup)
                            logger.debug(f"Sessão restaurada após erro ao obter chaves para {normalized_sender_jid}")
                        except Exception as e:
                            logger.warning(f"Erro ao restaurar sessão: {e}")
                    # Marca Future como concluída com erro e remove da fila
                    if future and not future.done():
                        future.set_exception(Exception(f"Erro ao obter chaves: {error_jids}"))
                    async with self._pending_pkmsg_sync_lock:
                        if normalized_sender_jid in self._pending_pkmsg_sync_requests:
                            if self._pending_pkmsg_sync_requests[normalized_sender_jid] == future:
                                del self._pending_pkmsg_sync_requests[normalized_sender_jid]
                                logger.debug(f"PKMSG de sincronização removido da fila após erro ao obter chaves para {normalized_sender_jid}")
                    return
                
                # Obtém mediatype do proto node (seguindo padrão de _send_as_pkmsg)
                mediatype = proto_node.get_attribute("mediatype") if proto_node else "text"
                
                # Encripta como PreKeyWhisperMessage (PKMSG)
                # Como deletamos a sessão, isso deve forçar PKMSG
                ciphertext = await self.axolotl_manager.encrypt(recipient_id, proto_bytes)
                
                # Identifica tipo (seguindo padrão de _send_as_pkmsg)
                if isinstance(ciphertext, PreKeyWhisperMessage):
                    enc_type = EncEntity.TYPE_PKMSG
                else:
                    enc_type = EncEntity.TYPE_MSG
                
                # Cria node <enc> usando EncEntity helper (seguindo padrão de _send_as_pkmsg)
                # Para PKMSG em mensagens normais (não peer), sempre precisa do <to> wrapper
                # dentro de <participants>, então sempre usa normalized_sender_jid
                # Para grupos com participant, usa jid do participant (normalized_sender_jid)
                # Para contatos individuais, também usa normalized_sender_jid para criar <to> wrapper
                enc_jid = normalized_sender_jid

                logger.debug(f"Enc_jid: {enc_jid}")
                
                enc_node = EncEntity.create_enc_node(
                    enc_type=enc_type,
                    ciphertext=ciphertext.serialize(),
                    mediatype=mediatype,
                    jid=enc_jid
                )
                
                # Constrói node final usando EncryptedMessageBuilder (seguindo padrão de _send_as_pkmsg)
                message_node = EncryptedMessageBuilder.build_encrypted_message(
                    message_node=message_node,
                    enc_entities=[enc_node],
                    participant=participant if participant else None
                )
                
                # Obtém tctoken se necessário
                tctoken = None
                if hasattr(self, 'axolotl_manager') and hasattr(self.axolotl_manager, '_store'):
                    tctoken = await self.axolotl_manager._store.getTcToken(normalized_sender_jid)
                
                # Adiciona elementos extras
                await self._add_message_extras(message_node, tctoken=tctoken)
                
                # Enfileira mensagem antes de enviar (para retry)
                self._enqueue_sent_message(message_node)
                
                # Envia
                await self._send_protocol_node(message_node)
                
                logger.info(f"PKMSG de sincronização enviado para {normalized_sender_jid} (sync_message_id={sync_message_id})")
                
                # Marca Future como concluída com sucesso
                if not future.done():
                    future.set_result(None)
            
            except Exception as e:
                logger.error(f"Erro ao enviar PKMSG para sincronização: {e}", exc_info=True)
                # Restaura sessão se houver backup e erro
                if had_session and session_backup and recipient_id_split is not None and deviceid is not None:
                    try:
                        await self.axolotl_manager._store.storeSession(recipient_id_split, deviceid, session_backup)
                        logger.debug(f"Sessão restaurada após erro para {normalized_sender_jid}")
                    except Exception as restore_error:
                        logger.warning(f"Erro ao restaurar sessão: {restore_error}")
                
                # Marca Future como concluída com erro
                if not future.done():
                    future.set_exception(e)
            
            finally:
                # Remove da fila após conclusão (sucesso ou erro)
                async with self._pending_pkmsg_sync_lock:
                    if normalized_sender_jid in self._pending_pkmsg_sync_requests:
                        # Verifica se é o mesmo future (pode ter sido substituído)
                        if self._pending_pkmsg_sync_requests[normalized_sender_jid] == future:
                            del self._pending_pkmsg_sync_requests[normalized_sender_jid]
                            logger.debug(f"PKMSG de sincronização concluído para {normalized_sender_jid}, removido da fila")
        
        except Exception as e:
            logger.error(f"Erro ao enviar PKMSG para sincronização: {e}", exc_info=True)
            # Remove da fila em caso de erro não tratado
            if normalized_sender_jid and future:
                async with self._pending_pkmsg_sync_lock:
                    if normalized_sender_jid in self._pending_pkmsg_sync_requests:
                        if self._pending_pkmsg_sync_requests[normalized_sender_jid] == future:
                            del self._pending_pkmsg_sync_requests[normalized_sender_jid]
                            logger.debug(f"PKMSG de sincronização removido da fila após erro não tratado para {normalized_sender_jid}")
    
    async def _send_retry_receipt(self, retry_receipt: ProtocolNode) -> None:
        """
        Envia retry receipt para solicitar reenvio de mensagem.
        
        Baseado em AxolotlReceiveLayer.send_retry() do zowsuplib.
        
        Args:
            retry_receipt: RetryOutgoingReceiptProtocolEntity a ser enviado
        """
        try:
            logger.debug(f"Enviando retry receipt: {retry_receipt}")
            await self._send_protocol_node(retry_receipt)
        except Exception as e:
            logger.error(f"Erro ao enviar retry receipt: {e}", exc_info=True)
    
    async def _send_receipt_on_error(
        self, message_id: str, from_jid: str, participant: Optional[str]
    ) -> None:
        """
        Envia OutgoingReceipt (delivered) em erros de descriptografia.
        Fluxo zowsuplib: InvalidKeyId, Duplicate, Unknown type, InvalidMessage após 2 retries.
        """
        from .builders.receipt_builder import ReceiptBuilder

        receipt_node = ReceiptBuilder.build_receipt(
            message_id=message_id,
            from_jid=from_jid,
            receipt_type=ReceiptBuilder.TYPE_DELIVERED,
            participant=participant,
        )
        await self._send_protocol_node(receipt_node)
        logger.debug(f"Receipt de erro enviado: id={message_id}, to={from_jid}")

    async def _get_registration_id(self) -> Optional[int]:
        """
        Obtém registration ID do cliente.
        
        Returns:
            int: Registration ID ou None se não disponível
        """
        try:
            if hasattr(self, 'axolotl_manager') and self.axolotl_manager:
                registration_id = self.axolotl_manager.registration_id
                return registration_id
            return None
        except Exception as e:
            logger.error(f"Erro ao obter registration_id: {e}", exc_info=True)
            return None
    
    async def mark_as_read(
        self,
        message_ids: Union[str, List[str]],
        from_jid: str,
        participant: Optional[str] = None
    ) -> None:
        """
        Marca mensagem(s) como lida(s) enviando receipt de leitura.
        
        Baseado em OutgoingReceiptProtocolEntity do zowsuplib.
        
        Args:
            message_ids: ID da mensagem ou lista de IDs de mensagens
            from_jid: JID do remetente (destinatário do receipt)
            participant: Participante (para grupos, opcional)
        
        Raises:
            RuntimeError: Se cliente não estiver autenticado
        
        Exemplo:
            # Marcar uma mensagem como lida
            await client.mark_as_read(
                message_ids="MESSAGE_ID",
                from_jid="5511999999999@s.whatsapp.net"
            )
            
            # Marcar múltiplas mensagens como lidas
            await client.mark_as_read(
                message_ids=["ID1", "ID2", "ID3"],
                from_jid="5511999999999@s.whatsapp.net"
            )
            
            # Marcar mensagem de grupo como lida
            await client.mark_as_read(
                message_ids="MESSAGE_ID",
                from_jid="GROUP_ID@g.us",
                participant="5511999999999@s.whatsapp.net"
            )
        """
        if not self._authenticated:
            raise RuntimeError("Cliente não está autenticado. Conecte-se primeiro.")
        
        try:
            from .builders.receipt_builder import ReceiptBuilder
            
            # Constrói receipt de leitura
            receipt_node = ReceiptBuilder.build_receipt(
                message_id=message_ids,
                from_jid=from_jid,
                receipt_type=ReceiptBuilder.TYPE_READ,
                participant=participant
            )
            
            logger.debug(
                f"Enviando receipt de leitura: "
                f"message_ids={message_ids}, from_jid={from_jid}, participant={participant}"
            )
            
            # Envia receipt
            await self._send_protocol_node(receipt_node)
            
            logger.info(
                f"Receipt de leitura enviado com sucesso: "
                f"message_ids={message_ids}, to={from_jid}"
            )
            
        except Exception as e:
            logger.error(f"Erro ao enviar receipt de leitura: {e}", exc_info=True)
            raise
    
    # ============================================================
    # Métodos de Proxy (API pública moderna)
    # ============================================================
    
    @classmethod
    async def new_proxy(cls, proxy_string: str, proxy_type: str = "http", test_url: str = "https://www.google.com") -> bool:
        """
        Cria novo proxy.
        Args:
            proxy_string: String de proxy no formato:
                         - "host:port" (sem autenticação)
                         - "host:port:username:password" (com autenticação)
                         - "DIRECT" (desativa proxy)
            proxy_type: Tipo de proxy ("socks5" ou "http"), padrão "socks5"
            test_url: URL para testar proxy antes de configurar
            
        Returns:
            bool: True se criado com sucesso, False se falhou

        """

        try:
            proxy_config = ProxyConfig.from_string(proxy_string, proxy_type=proxy_type)
        except ValueError as e:
            logger.error(f"Erro no formato do proxy: {e}")
            raise
        
        # 2. Testa proxy (async)
        if not await cls._test_proxy(proxy_config, test_url):
            logger.warning(f"Proxy {proxy_config} falhou no teste, mas será configurado")
            # Não retorna False, permite configurar mesmo se teste falhar
            return False

        return proxy_config
    
    async def set_proxy(
        self,
        proxy_string: str,
        proxy_type: str = "http",
        test_url: str = "https://www.google.com"
    ) -> bool:
        """
        Configura proxy para conexões futuras.
        
        Valida e testa o proxy antes de configurar. Salva no banco de dados.
        
        Args:
            proxy_string: String de proxy no formato:
                         - "host:port" (sem autenticação)
                         - "host:port:username:password" (com autenticação)
                         - "DIRECT" (desativa proxy)
            proxy_type: Tipo de proxy ("socks5" ou "http"), padrão "socks5"
            test_url: URL para testar proxy antes de configurar
            
        Returns:
            bool: True se configurado com sucesso, False se falhou
            
        Raises:
            ValueError: Se formato inválido
            
        Exemplos:
            # Proxy SOCKS5 sem autenticação
            await client.set_proxy("192.168.1.100:1080")
            
            # Proxy SOCKS5 com autenticação
            await client.set_proxy("192.168.1.100:1080:user:pass")
            
            # Proxy HTTP CONNECT
            await client.set_proxy("192.168.1.100:8080", proxy_type="http")
            
            # Desativar proxy
            await client.set_proxy("DIRECT")
        """
        # 1. Valida e parse
        if proxy_string.upper() == "DIRECT":
            self.network_config = NetworkConfig.direct()
            self.proxy = None
            await self._remove_proxy_from_db()
            logger.info(f"PROXY desativado - conexão direta (conta: {self.account_id})")
            return True
        

        proxy_config = await self.new_proxy(proxy_string=proxy_string,proxy_type=proxy_type,test_url=test_url)
        if not proxy_config:
            return False
        
        # 3. Configura na instância
        self.network_config = NetworkConfig.proxy_config(proxy_config)
        self.proxy = proxy_config.to_dict()
        
        # 4. Salva no banco
        await self._save_proxy_to_db(proxy_config)
        
        logger.info(f"PROXY configurado: {proxy_config.proxy_type.upper()} {proxy_config.host}:{proxy_config.port} (conta: {self.account_id})")
        return True
    
    async def get_proxy(self) -> Optional[str]:
        """
        Obtém configuração de proxy do banco de dados.
        
        Returns:
            String de proxy no formato "host:port[:username:password]" ou None
        """
        # Primeiro tenta obter da instância atual
        if self.network_config and self.network_config.type == "proxy" and self.network_config.proxy:
            return self.network_config.proxy.to_dict()
        
        # Se não tem na instância, carrega do banco
        proxy_config = await self._load_proxy_from_db()
        if proxy_config:
            return proxy_config.to_dict()
        
        return None
    

    async def get_proxy_status(self) -> bool:
        """Obtém status do proxy."""
        if not self.network_config or not self.network_config.proxy:
            return False
        return True
    
    async def remove_proxy(self) -> bool:
        """
        Remove configuração de proxy.
        
        Returns:
            bool: True se removido com sucesso
        """
        self.network_config = NetworkConfig.direct()
        self.proxy = None
        await self._remove_proxy_from_db()
        logger.info(f"PROXY removido - conexão direta (conta: {self.account_id})")
        return True
    
    async def _load_proxy_from_db(self) -> Optional[ProxyConfig]:
        """Carrega proxy do banco de dados e configura na instância."""
        if not self.session_maker:
            return None
        
        try:
            from ..db.models import Account
            from sqlalchemy import select
            
            async with self.session_maker() as session:
                result = await session.execute(
                    select(Account).filter_by(phone=self.account_id)
                )
                account = result.scalar_one_or_none()
                
                if account and account.proxy_host and account.proxy_port:
                    proxy_config = ProxyConfig(
                        host=account.proxy_host,
                        port=account.proxy_port,
                        username=account.proxy_username,
                        password=account.proxy_password,
                        proxy_type=getattr(account, 'proxy_type', None) or "socks5"
                    )
                    
                    # Configura na instância
                    self.network_config = NetworkConfig.proxy_config(proxy_config)
                    self.proxy = proxy_config.to_dict()
                    
                    logger.info(f"PROXY carregado do banco de dados: {proxy_config.proxy_type.upper()} {proxy_config.host}:{proxy_config.port} (conta: {self.account_id})")
                    return proxy_config
        except Exception as e:
            logger.warning(f"Erro ao carregar proxy do banco: {e}")
        
        return None
    
    async def _save_proxy_to_db(self, proxy_config: ProxyConfig) -> None:
        """Salva proxy no banco de dados."""
        if not self.session_maker:
            logger.debug("db_pool não disponível, pulando salvamento de proxy")
            return
        
        try:
            from ..db.models import Account
            from sqlalchemy import select
            
            async with self.session_maker() as session:
                result = await session.execute(
                    select(Account).filter_by(phone=self.account_id)
                )
                account = result.scalar_one_or_none()
                
                if account:
                    account.proxy_host = proxy_config.host
                    account.proxy_port = proxy_config.port
                    account.proxy_username = proxy_config.username
                    account.proxy_password = proxy_config.password
                    # Note: proxy_type não está no modelo Account ainda, mas não quebra
                    if hasattr(account, 'proxy_type'):
                        account.proxy_type = proxy_config.proxy_type
                    
                    await session.commit()
                    logger.info(f" PROXY salvo no banco de dados: {proxy_config.proxy_type.upper()} {proxy_config.host}:{proxy_config.port} (conta: {self.account_id})")
                else:
                    logger.warning(f"Account {self.account_id} não encontrado no banco")
        except Exception as e:
            logger.warning(f"Erro ao salvar proxy no banco: {e}")
    
    async def _remove_proxy_from_db(self) -> None:
        """Remove proxy do banco de dados."""
        if not self.session_maker:
            return
        
        try:
            from ..db.models import Account
            from sqlalchemy import select
            
            async with self.session_maker() as session:
                result = await session.execute(
                    select(Account).filter_by(phone=self.account_id)
                )
                account = result.scalar_one_or_none()
                
                if account:
                    account.proxy_host = None
                    account.proxy_port = None
                    account.proxy_username = None
                    account.proxy_password = None
                    if hasattr(account, 'proxy_type'):
                        account.proxy_type = None
                    
                    await session.commit()
                    logger.info(f"🌐 PROXY removido do banco de dados (conta: {self.account_id})")
        except Exception as e:
            logger.warning(f"Erro ao remover proxy do banco: {e}")
    

    @classmethod
    async def _test_proxy(cls, proxy_config: ProxyConfig, test_url: str) -> bool:
        """Testa proxy fazendo requisição HTTP."""
        import urllib.request
        import urllib.error
        
        try:
            proxy_url = f"http://{proxy_config.host}:{proxy_config.port}"
            if proxy_config.username and proxy_config.password:
                proxy_url = f"http://{proxy_config.username}:{proxy_config.password}@{proxy_config.host}:{proxy_config.port}"
            
            proxy_handler = urllib.request.ProxyHandler({
                'http': proxy_url,
                'https': proxy_url
            })
            
            opener = urllib.request.build_opener(proxy_handler)
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')]
            
            req = urllib.request.Request(test_url)
            with opener.open(req, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Proxy testado com sucesso: {proxy_config}")
                    return True
                else:
                    logger.warning(f"Proxy respondeu com status {response.status}")
                    return False
                    
        except urllib.error.URLError as e:
            logger.warning(f"Proxy falhou no teste: {e}")
            return False
        except Exception as e:
            logger.warning(f"Erro ao testar proxy: {e}")
            return False






