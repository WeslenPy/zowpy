"""
WhatsApp Client V2 - Cliente com fluxo linear assíncrono.

Baseado no zowsuplib, mas totalmente assíncrono e sem eventos complexos.
Fluxo direto: conexão → handshake → autenticação.
"""

import asyncio
import base64
import random
import time
from typing import Optional, Dict, Any, Tuple, List, Union
from loguru import logger

# from zowpy.axolotl.state.prekeyrecord import PreKeyRecord
from zowpy.db.factory import AxolotlManagerFactory
from zowpy.profile.profile import AsyncProfile
from zowpy.config.v1.config import Config
from zowpy.utils.tools import WATools
from zowpy.config.bot_env import BotEnv

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
        db_pool=None,
        device_config=None,
        proxy: Optional[Dict[str, any]] = None,
    ):
        """
        Inicializa cliente WhatsApp.
        
        Args:
            account_id: ID da conta (número de telefone)
            endpoint: Endpoint TCP do WhatsApp (host, port)
            db_pool: Pool de banco de dados
            device_config: Configuração do dispositivo
            proxy: Configuração de proxy (opcional)
        """
        self.account_id = normalize(account_id)
        self.endpoint = endpoint or (f"e{random.randint(1, 16)}.whatsapp.net", 5222)
        self.proxy = proxy
        self.db_pool = db_pool
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
        
        # Estado
        self._running = False
        self._connected = False
        self._authenticated = False
        
        # Prekeys não enviadas e retry
        self._unsent_prekeys: List = []
        self._pending_keys_retry: Optional[Tuple] = None
        self._keys_retry_lock = asyncio.Lock()
        
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
            await self._load_prekeys()
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
            
            # 3. Conecta TCP socket
            logger.info("Conectando TCP socket...")
            self.connection = AsyncConnection(self.endpoint, proxy=self.proxy)
            await self.connection.connect()
            logger.info("✓ TCP socket conectado")
            
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
            logger.info("Enviando stream:stream...")
            await self._send_stream_start()
            logger.info("✓ stream:stream enviado")
            
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
        # Profile
        self.profile = AsyncProfile(self.account_id, db_pool=self.db_pool)
        
        # State store
        self.state_store = AsyncStateStore(self.account_id, self.db_pool)
        
        # Axolotl manager
        factory = AxolotlManagerFactory(db_pool=self.db_pool)
        self.axolotl_manager = await factory.get_manager(self.account_id, self.account_id)
        
        # Coder (sem eventos - versão simplificada)
        # TODO: Criar AsyncCoder sem eventos se necessário
        from ..core.events import AsyncEventEmitter
        events = AsyncEventEmitter()
        self.coder = AsyncCoder(events)
        
        # Handlers (legacy - mantidos para compatibilidade)
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
        
        self._node_router.register(AckProcessor(self.events))
        self._node_router.register(PresenceProcessor(self.events))
        # IQProcessor precisa do IQResponseProcessor para chamar callbacks
        self._node_router.register(IQProcessor(self.events, self._iq_response_processor))
        
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
        except Exception as e:
            logger.warning(f"Erro ao gerar prekeys (não crítico): {e}")
    
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
        """
        logger.info("Enviando <auth> com credenciais...")
        
        # Obtém username do profile
        username = await self.profile.username if self.profile else None
        if not username:
            username = self.account_id.replace("+", "").replace("-", "").replace(" ", "")
        
        # Cria node <auth> conforme protocolo WhatsApp
        auth_node = ProtocolNode(
            tag="auth",
            attributes={
                "mechanism": "WAUTH-2",
                "user": str(username),
            }
        )
        
        await self._send_protocol_node(auth_node)
        logger.info(f"✓ <auth> enviado com user={username}")
    
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
        if not self.db_pool:
            logger.debug("db_pool não disponível, pulando atualização de status")
            return
        
        try:
            from ..db.models import Account
            from sqlalchemy import select
            
            async with self.db_pool.get_session() as session:
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
        """Loop de processamento de mensagens."""
        logger.info("Message loop iniciado")
        
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
                
                # Processa node usando router (passa dados descriptografados)
                # O router/processor vai descriptografar novamente se necessário
                await self._process_protocol_node(node, raw_data=decrypted)
                
            except asyncio.TimeoutError:
                continue
            except StreamCancelledError:
                logger.info("Stream cancelado, encerrando message loop")
                break
            except Exception as e:
                logger.error(f"Erro no message loop: {e}")
                await asyncio.sleep(0.1)
    
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
        
        # Atualiza EncryptionReceiver com funções disponíveis
        if self._encryption_receiver:
            self._encryption_receiver._get_keys = self._get_keys_for_recipient
            self._encryption_receiver._process_pending = self._process_pending_messages
            self._encryption_receiver._send_pkmsg_for_invalid_message = self._send_pkmsg_for_invalid_message
            self._encryption_receiver._send_retry_receipt_fn = self._send_retry_receipt
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
                await asyncio.sleep(30)
                if self._connected and self._authenticated:
                    await self._send_keepalive()
            except Exception as e:
                logger.error(f"Erro no keepalive: {e}")
    
    async def _send_keepalive(self) -> None:
        """Envia keepalive."""
        keepalive_node = ProtocolNode(
            tag="iq",
            attributes={
                "id": f"keepalive_{int(time.time())}",
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
        
        to_jid = to_whatsapp_jid(to)
        is_group = to_jid.endswith(f"@{YowConstants.WHATSAPP_GROUP_SERVER}")
        
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
        Envia mensagem para contato individual.
        
        Fluxo baseado em AxolotlSendLayer.processPlaintextNodeAndSend():
        1. Verifica se precisa sincronizar dispositivos
        2. Verifica quais dispositivos têm sessão
        3. Obtém chaves para dispositivos sem sessão
        4. Criptografa para cada dispositivo
        5. Envia
        """
        account = to_jid.split('@')[0]
        
        # Verifica se tem dispositivo específico (ex: 123456789:0)
        if ":" in account:
            # Dispositivo específico
            jids = [to_jid]
            await self._send_to_contacts_with_sessions(message_node, proto_bytes, jids)
        elif "lid" in to_jid:
            # LID (Linked ID)
            jids = [to_jid]
            await self._send_to_contacts_with_sessions(message_node, proto_bytes, jids)
        else:
            # Precisa sincronizar dispositivos primeiro
            recipient_id = account
            
            # Obtém todas as sessões existentes para este recipient
            session_jids = await self.axolotl_manager.get_all_session_usernames(recipient_id)
            
            if session_jids:
                # Tem sessões, envia para elas
                await self._send_to_contacts_with_sessions(message_node, proto_bytes, session_jids)
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
        
        # Adiciona elementos extras
        await self._add_message_extras(message_node)
        
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
                jid=None
            )
            
            # Constrói node final usando EncryptedMessageBuilder
            message_node = EncryptedMessageBuilder.build_encrypted_message(
                message_node=message_node,
                enc_entities=[enc_node],
                participant=None
            )
            
            # Adiciona elementos extras
            await self._add_message_extras(message_node)
            
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
                
                future.set_result((success_jids, error_jids))
            
            except Exception as e:
                logger.error(f"Erro ao processar resposta de get keys: {e}", exc_info=True)
                future.set_exception(e)
        
        async def on_error(error_node: ProtocolNode):
            """Callback de erro"""
            error_jids[recipient_jid] = Exception(f"Erro ao obter chaves: {error_node.get_attribute('type')}")
            future.set_result(([], error_jids))
        
        # Registra callbacks e envia
        self._iq_response_processor.register_callback(iq_id, on_success, timeout=30.0)
        await self._send_protocol_node(iq_node)
        
        try:
            # Aguarda resposta
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            self._iq_response_processor.unregister_callback(iq_id)
            logger.error(f"Timeout ao obter chaves para {recipient_jid}")
            return ([], {recipient_jid: Exception("Timeout ao obter chaves")})
        except Exception as e:
            self._iq_response_processor.unregister_callback(iq_id)
            logger.error(f"Erro ao obter chaves para {recipient_jid}: {e}")
            return ([], {recipient_jid: e})
    
    async def _send_to_group(self, message_node: ProtocolNode, proto_bytes: bytes) -> None:
        """
        Envia mensagem para grupo.
        
        Baseado em AxolotlSendLayer.sendToGroupWithSessions()
        Por enquanto, implementa versão simplificada sem sender key distribution.
        """
        
        group_jid = message_node.get_attribute("to")
        
        # Obtém mediatype do proto node
        proto_node = message_node.get_child("proto")
        mediatype = proto_node.get_attribute("mediatype") if proto_node else "text"
        
        enc_entities = []
        
        try:
            # Criptografa com sender key do grupo
            ciphertext = await self.axolotl_manager.group_encrypt(group_jid, proto_bytes)
            
            # Cria node <enc> como SKMSG usando EncEntity helper
            skmsg_node = EncEntity.create_enc_node(
                enc_type=EncEntity.TYPE_SKMSG,
                ciphertext=ciphertext,
                mediatype=mediatype,
                jid=None
            )
            
            enc_entities.append(skmsg_node)
            
        except Exception as e:
            # Verifica se é NoSessionException
            if "NoSessionException" in str(type(e)) or "No session" in str(e) or "No sender key" in str(e):
                # Sender key não existe, criar antes
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
            else:
                raise
        
        # Constrói node final usando EncryptedMessageBuilder
        message_node = EncryptedMessageBuilder.build_encrypted_message(
            message_node=message_node,
            enc_entities=enc_entities,
            participant=None
        )
        
        # Adiciona elementos extras
        await self._add_message_extras(message_node)
        
        # Enfileira mensagem antes de enviar (para retry)
        self._enqueue_sent_message(message_node)
        
        # Envia
        await self._send_protocol_node(message_node)
    
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
        """Desconecta de forma assíncrona."""
        logger.info("Desconectando...")
        
        self._running = False
        self._connected = False
        self._authenticated = False
        
        # Para bridge
        if self.bridge:
            await self.bridge.stop()
        
        # Cancela stream
        if self.stream:
            await self.stream.cancel()
        
        # Cancela tasks
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
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Desconecta TCP
        if self.connection:
            await self.connection.disconnect()
        
        # Emite evento de desconexão
        await self.events.emit("disconnected", {"account_id": self.account_id})
        
        logger.info("Desconectado")
    
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
    
    async def _check_and_flush_prekeys(self) -> None:
        """
        Verifica e envia prekeys não enviadas.
        
        Baseado em AxolotlControlLayer.onAuthed()
        """
        try:
            # Carrega prekeys não enviadas
            unsent_prekeys_result = await self.axolotl_manager.load_unsent_prekeys()
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
        
        # Armazena informações para retry se necessário
        async with self._keys_retry_lock:
            self._pending_keys_retry = (signed_prekey, prekeys, reboot_connection, retry_count)
        
        # Prepara dicionário de prekeys
        # CORREÇÃO: Ajustar IDs antes de passar para o builder (como no zowsuplib)
        logger.info("[ZOWPY] Preparando prekeys_dict (comparação com zowsuplib)...")
        prekeys_dict = {}
        for prekey in prekeys:
            key_pair = prekey.getKeyPair()
            # Serializa public key (remove primeiro byte)
            public_key_bytes = key_pair.getPublicKey().serialize()[1:]
            # Ajusta array e ID (como no zowsuplib)
            adjusted_key = PrekeyBuilder._adjust_array(public_key_bytes)
            prekey_id = prekey.getId()
            adjusted_id = PrekeyBuilder._adjust_id(prekey_id)  # Ajusta ID aqui
            prekeys_dict[adjusted_id] = adjusted_key  # Usa bytes ajustado como chave
            
            # Log detalhado para comparação
            logger.debug(f"[ZOWPY] Prekey preparado: id_int={prekey_id}, id_ajustado_len={len(adjusted_id)}, public_key_raw_len={len(public_key_bytes)}, adjusted_key_len={len(adjusted_key)}")
        
        logger.info(f"[ZOWPY] prekeys_dict criado com {len(prekeys_dict)} prekeys (chaves são bytes ajustados, valores são bytes ajustados)")
        
        # Prepara signed prekey
        # CORREÇÃO: Ajustar ID antes de passar para o builder (como no zowsuplib)
        logger.info("[ZOWPY] Preparando signed_prekey (comparação com zowsuplib)...")
        signed_prekey_id = signed_prekey.getId()
        adjusted_signed_id = PrekeyBuilder._adjust_id(signed_prekey_id)  # Ajusta ID aqui
        signed_public_key = signed_prekey.getKeyPair().getPublicKey().serialize()[1:]
        signed_adjusted_key = PrekeyBuilder._adjust_array(signed_public_key)
        signed_signature = signed_prekey.getSignature()
        signed_adjusted_sig = PrekeyBuilder._adjust_array(signed_signature)
        signed_key_tuple = (adjusted_signed_id, signed_adjusted_key, signed_adjusted_sig)  # ID já ajustado (bytes)
        
        logger.info(f"[ZOWPY] Signed prekey preparado: id_int={signed_prekey_id}, id_ajustado_len={len(adjusted_signed_id)}, public_key_raw_len={len(signed_public_key)}, adjusted_key_len={len(signed_adjusted_key)}, signature_raw_len={len(signed_signature)}, adjusted_sig_len={len(signed_adjusted_sig)}")
        
        # Prepara identity key
        logger.info("[ZOWPY] Preparando identity_key (comparação com zowsuplib)...")
        identity_public_key = self.axolotl_manager.identity.getPublicKey().serialize()[1:]
        adjusted_identity = PrekeyBuilder._adjust_array(identity_public_key)
        logger.info(f"[ZOWPY] Identity key preparado: raw_len={len(identity_public_key)}, adjusted_len={len(adjusted_identity)}")
        
        # Prepara registration ID
        # CORREÇÃO: Ajustar registration ID antes de passar para o builder (como no zowsuplib)
        registration_id_int = self.axolotl_manager.registration_id
        adjusted_registration_id = PrekeyBuilder._adjust_id(registration_id_int, byte_count=4)  # Ajusta ID aqui
        logger.info(f"[ZOWPY] Registration ID: {registration_id_int} (int) -> ajustado: {len(adjusted_registration_id)} bytes")
        
        # Cria IQ node
        logger.info("[ZOWPY] Chamando PrekeyBuilder.build_set_keys_iq()...")
        logger.info(f"[ZOWPY] Parâmetros: prekeys_dict_len={len(prekeys_dict)}, registration_id_ajustado_len={len(adjusted_registration_id)}, djb_type=5")
        logger.info("[ZOWPY] Comparação esperada com zowsuplib:")
        logger.info("[ZOWSUPLIB] SetKeysIqProtocolEntity(identityKey, signedPreKey, preKeys, Curve.DJB_TYPE, registrationId)")
        logger.info("[ZOWSUPLIB] - identityKey: bytes ajustados (adjustArray)")
        logger.info("[ZOWSUPLIB] - signedPreKey: tuple(id_ajustado, key_ajustado, sig_ajustado)")
        logger.info("[ZOWSUPLIB] - preKeys: dict{id_ajustado: key_ajustado}")
        logger.info("[ZOWSUPLIB] - djbType: 5 (Curve.DJB_TYPE)")
        logger.info("[ZOWSUPLIB] - registrationId: bytes ajustados (adjustId, byte_count=4)")
        
        iq_node = PrekeyBuilder.build_set_keys_iq(
            identity_key=adjusted_identity,
            signed_prekey=signed_key_tuple,
            prekeys=prekeys_dict,
            registration_id=adjusted_registration_id,  # Passa bytes ajustado
            djb_type=5,  # Curve.DJB_TYPE
            iq_id=None  # Será gerado
        )
        
        iq_id = iq_node.get_attribute("id")
        logger.info(f"[ZOWPY] IQ node criado com ID: {iq_id}")
   
        async def on_error(node: ProtocolNode):
            """Callback de erro"""
            logger.info(f"Callback flush keys  de erro: {node}")
            await self._on_sent_keys_error(node, iq_node, signed_prekey, prekeys, reboot_connection, retry_count)
        

        async def on_success(node):
            await self._on_keys_flushed(prekeys, reboot_connection=reboot_connection)

        # Registra callbacks e envia
        # O IQResponseProcessor processa automaticamente erros se o tipo for "error"

        self._iq_response_processor.register_callback(iq_id, on_success, timeout=30.0)
        # Para erros, vamos verificar no process_iq_response

        await self._send_protocol_node(iq_node)
        
        logger.info(f"Prekeys enviadas: {len(prekeys)} prekeys, signed_prekey_id={signed_prekey.getId()}")
    
    async def _on_keys_flushed(self, prekeys: list, reboot_connection: bool = False) -> None:
        """
        Callback quando prekeys são enviadas com sucesso.
        
        Baseado em AxolotlControlLayer.on_keys_flushed()
        """
        async with self._keys_retry_lock:
            self._pending_keys_retry = None
      
        
        await self.axolotl_manager.set_prekeys_as_sent(prekeys)
        
        logger.info(f"Prekeys marcadas como enviadas: {len(prekeys)} prekeys")
        
        if reboot_connection:
            logger.info("Reiniciando conexão após envio de prekeys...")
            # Reconecta usando o método reconnect
            await self.reconnect()
    
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
        participant_jid: Optional[str] = None
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
        
        Args:
            from_jid: JID do remetente (pode ser grupo ou contato)
            message_id: ID da mensagem que falhou
            participant: Participante (para grupos, opcional)
        """
        try:
            from ..utils.tools import WATools

            sender_jid = participant if participant else from_jid
            
            # Normaliza JID se necessário (baseado em zowsuplib)
            normalized_sender_jid = WATools.normalizeJid(from_jid)
            
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
            
            # Adiciona node <proto>
            proto_node = ProtocolNode(
                tag="proto",
                attributes={},
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
                    return
                
                # Obtém mediatype do proto node
                mediatype = "text"  # Mensagem de texto vazia
                
                # Encripta como PreKeyWhisperMessage (PKMSG)
                # Como deletamos a sessão, isso deve forçar PKMSG
                ciphertext = await self.axolotl_manager.encrypt(recipient_id, proto_bytes)
                
                # Verifica se é PreKeyWhisperMessage (deve ser, já que deletamos a sessão)
                # Baseado em zowsuplib: if ciphertext.__class__ != PreKeyWhisperMessage
                if not isinstance(ciphertext, PreKeyWhisperMessage):
                    logger.warning(f"Esperado PreKeyWhisperMessage, mas obteve {ciphertext.__class__.__name__}")
                
                # Cria node <enc> com TYPE_PKMSG
                # Baseado em zowsuplib: EncProtocolEntity(TYPE_PKMSG, 2, ciphertext.serialize(), mediaType)
                enc_node = EncEntity.create_enc_node(
                    enc_type=EncEntity.TYPE_PKMSG,  # Força PKMSG
                    ciphertext=ciphertext.serialize(),
                    mediatype=mediatype,
                    jid=None
                )
                
                # Constrói node final usando EncryptedMessageBuilder
                message_node = EncryptedMessageBuilder.build_encrypted_message(
                    message_node=message_node,
                    enc_entities=[enc_node],
                    participant=participant if participant else None
                )
                
                # Adiciona elementos extras
                await self._add_message_extras(message_node)
                
                # Enfileira mensagem antes de enviar (para retry)
                self._enqueue_sent_message(message_node)
                
                # Envia
                await self._send_protocol_node(message_node)
                
                logger.info(f"PKMSG de sincronização enviado para {normalized_sender_jid} (sync_message_id={sync_message_id})")
            
            except Exception as e:
                logger.error(f"Erro ao enviar PKMSG para sincronização: {e}", exc_info=True)
                # Restaura sessão se houver backup e erro
                if had_session and session_backup and recipient_id_split is not None and deviceid is not None:
                    try:
                        await self.axolotl_manager._store.storeSession(recipient_id_split, deviceid, session_backup)
                        logger.debug(f"Sessão restaurada após erro para {normalized_sender_jid}")
                    except Exception as restore_error:
                        logger.warning(f"Erro ao restaurar sessão: {restore_error}")
        
        except Exception as e:
            logger.error(f"Erro ao enviar PKMSG para sincronização: {e}", exc_info=True)
    
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





