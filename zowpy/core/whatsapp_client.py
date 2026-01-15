"""
WhatsApp Client Completo - Cliente principal com fluxo completo.

Implementa todo o fluxo de conexão, manutenção online e envio/recebimento de mensagens.
"""

import asyncio
import base64
import time
import struct
from typing import Optional, Dict, Any, Tuple
from loguru import logger

from zowpy.db.factory import AxolotlManagerFactory
from zowpy.profile.profile import AsyncProfile
from zowpy.config.v1.config import Config
from zowpy.utils.tools import WATools
from zowpy.config.bot_env import BotEnv

from .connection import AsyncConnection
from .events import AsyncEventEmitter
from .store import AsyncStateStore
from ..noise.protocol import AsyncWANoiseProtocol
from ..noise.stream import AsyncSegmentedStream, StreamCancelledError
from ..noise.handshake import AsyncWAHandshake
from ..noise.config import ClientConfig
from ..protocol.coder import AsyncCoder
from ..protocol.messages import AsyncMessageHandler
from ..protocol.acks import AsyncAcksHandler
from ..protocol.receipts import AsyncReceiptHandler
from ..protocol.presence import AsyncPresenceHandler
from ..protocol.auth import AsyncAuthHandler
from ..protocol.structs import ProtocolNode
from ..db.manager import AxolotlManager
from ..utils.jid import normalize, to_whatsapp_jid
from .import_account import import_account_from_six_parts


class WhatsAppClient:
    """
    Cliente principal completo do WhatsApp.
    
    Integra todos os componentes e implementa o fluxo completo:
    - Conexão WebSocket
    - Handshake Noise
    - Manutenção de conexão online
    - Envio de mensagens
    - Recebimento de mensagens
    """
    
    def __init__(
        self,
        account_id: str,
        endpoint: Tuple[str, int] = ("e15.whatsapp.net", 5222),
        db_pool=None,
        device_config=None,
        proxy: Optional[Dict[str, any]] = None,
    ):
        """
        Inicializa cliente WhatsApp.
        
        :param account_id: ID da conta (número de telefone)
        :param endpoint: Endpoint TCP do WhatsApp (host, port)
        :param db_pool: Pool de banco de dados
        :param device_config: Configuração do dispositivo
        :param proxy: Configuração de proxy (opcional) {"host": "...", "port": ..., "type": "socks5", "username": "...", "password": "..."}
        """
        self.account_id = normalize(account_id)
        self.endpoint = endpoint
        self.proxy = proxy
        self.db_pool = db_pool
        self.device_config = device_config
        
        # Componentes principais
        self.connection: Optional[AsyncConnection] = None
        self.stream: Optional[AsyncSegmentedStream] = None
        self.noise_protocol: Optional[AsyncWANoiseProtocol] = None
        self.handshake: Optional[AsyncWAHandshake] = None
        self.coder: Optional[AsyncCoder] = None
        self.axolotl_manager: Optional[AxolotlManager] = None
        
        # Stores e handlers
        self.state_store: Optional[AsyncStateStore] = None
        self.message_handler: Optional[AsyncMessageHandler] = None
        self.acks_handler: Optional[AsyncAcksHandler] = None
        self.receipts_handler: Optional[AsyncReceiptHandler] = None
        self.presence_handler: Optional[AsyncPresenceHandler] = None
        self.auth_handler: Optional[AsyncAuthHandler] = None
        
        # Eventos de autenticação
        self._auth_event = asyncio.Event()
        self._auth_failed = False

        #config
        self._rs = None
        self._local_static = None
        self.profile:AsyncProfile = None
        self.config:Config = None
        self._remote_static = None
        
        # Eventos
        self.events = AsyncEventEmitter()
        
        # Estado
        self._running = False
        self._connected = False
        self._authenticated = False
        
        # Tasks
        self._message_loop_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._bridge_task: Optional[asyncio.Task] = None
        
        # Configuração
        self.client_config: Optional[ClientConfig] = None

        # Profile para acesso centralizado às informações da conta
        self._profile: Optional[AsyncProfile] = None

        # Bot environment para configurações de dispositivo e rede
        self.bot_env: Optional[BotEnv] = None
    
    async def connect(self) -> None:
        """
        Conecta ao WhatsApp de forma totalmente assíncrona.
        
        Fluxo completo:
        1. Conecta TCP socket
        2. Inicializa componentes
        3. Executa handshake Noise
        4. Inicia loops de processamento
        5. Mantém conexão online
        """
        try:
            logger.info(f"Conectando ao WhatsApp para {self.account_id}")
            
            # 1. Inicializa stores e handlers
            await self._initialize_components()
            
            # 2. Conecta TCP socket
            self.connection = AsyncConnection(
                self.endpoint,
                proxy=self.proxy,
                on_message=self._handle_tcp_message
            )
            await self.connection.connect()
            logger.info("TCP socket conectado")

            # 2.5. Cria stream primeiro (necessário para o protocolo)
            self.stream = AsyncSegmentedStream()

            # 2.6. Cria protocolo Noise
            logger.debug("Creating noise protocol")
            self.noise_protocol = AsyncWANoiseProtocol()
            logger.debug("Noise protocol created")

            # Registra callbacks
            logger.debug("Registering handshake complete callback")
            self.noise_protocol.on("handshake_complete", self._on_handshake_complete)
            logger.debug("Handshake complete callback registered")

            # 3. CRÍTICO: Bridge TCP Socket <-> Stream DEVE estar rodando ANTES do handshake
            # O handshake precisa do bridge ativo para enviar/receber dados
            logger.debug("Starting bridge TCP to Stream (ANTES do handshake)")
            self._running = True
            self._bridge_task = asyncio.create_task(self._bridge_tcp_to_stream())
            logger.debug("Bridge TCP to Stream started")

            # 4. Pequeno delay para garantir que o bridge está processando
            await asyncio.sleep(0.05)
            
            # 5. EVENT_STATE_CONNECTED: Gera prekeys e emite EVENT_AUTH
            # Seguindo o fluxo do zowsuplib:
            # - YowNetworkLayer.onConnected() → emite EVENT_STATE_CONNECTED
            # - YowAuthenticationProtocolLayer.on_connected() → emite EVENT_AUTH
            # - AxolotlControlLayer.on_connected() → chama level_prekeys()
            logger.debug("Calling _on_tcp_connected (bridge já está ativo)")
            await self._on_tcp_connected()
            
            # 6. EVENT_AUTH já foi emitido por _on_tcp_connected()
            # O handler _on_auth() será chamado automaticamente e iniciará o handshake
            # O bridge já está rodando, então o handshake pode começar imediatamente
            self._connected = True
            self._authenticated = False  # Aguarda autenticação
            self._auth_failed = False
            self._auth_event.clear()
            
            self._message_loop_task = asyncio.create_task(self._message_loop())
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            
            logger.info("Aguardando handshake iniciar e concluir...")
            
            # 7. Aguarda autenticação (com timeout)
            # O handshake será iniciado pelo handler _on_auth() que responde ao EVENT_AUTH
            try:
                await asyncio.wait_for(
                    self._wait_for_authentication(),
                    timeout=30.0
                )
                # Valida que realmente está autenticado
                if not self._authenticated:
                    raise RuntimeError("Evento de autenticação setado mas _authenticated=False")
                
                logger.info("Cliente autenticado com sucesso")
                await self.events.emit("authenticated", {"account_id": self.account_id})
                await self.events.emit("connected", {"account_id": self.account_id})
            except asyncio.TimeoutError:
                logger.error("Timeout aguardando autenticação após 30 segundos")
                logger.error(f"Estado: authenticated={self._authenticated}, auth_failed={self._auth_failed}")
                raise RuntimeError("Timeout aguardando autenticação")
            except Exception as e:
                logger.error(f"Erro na autenticação: {e}", exc_info=True)
                if self._auth_failed:
                    raise RuntimeError("Falha na autenticação")
                raise
            
        except Exception as e:
            logger.error(f"Erro ao conectar: {e}")
            await self.events.emit("connection:error", {"error": str(e)})
            raise
    
    async def _initialize_components(self) -> None:
        """Inicializa todos os componentes."""
        # Inicializa profile para acesso centralizado às informações da conta
        self.profile = AsyncProfile(self.account_id, db_pool=self.db_pool)

        # State store
        self.state_store = AsyncStateStore(self.account_id, self.db_pool)
        
        # Axolotl manager
        factory = AxolotlManagerFactory(db_pool=self.db_pool)
        self.axolotl_manager = await factory.get_manager(self.account_id, self.account_id)
        # AxolotlManager não precisa de initialize() - store inicializa quando necessário
        
        # Coder
        self.coder = AsyncCoder(self.events)
        
        # Handlers
        self.message_handler = AsyncMessageHandler(self.events)
        self.acks_handler = AsyncAcksHandler(self.events)
        self.receipts_handler = AsyncReceiptHandler(self.events)
        self.presence_handler = AsyncPresenceHandler(self.events)
        self.auth_handler = AsyncAuthHandler(self.events)
        
        # Registra handlers de eventos de autenticação
        # Seguindo o fluxo do zowsuplib:
        # - EVENT_STATE_CONNECTED → emite EVENT_AUTH → inicia handshake
        # - Handshake concluído → emite EVENT_AUTHED → aguarda success
        # - Success recebido → marca como autenticado
        self.events.on(AsyncAuthHandler.EVENT_AUTH, self._on_auth)  # Inicia handshake
        self.events.on(AsyncAuthHandler.EVENT_AUTHED, self._on_authenticated)  # Handshake concluído ou success
        self.events.on(AsyncAuthHandler.EVENT_FAILURE, self._on_auth_failure)
        self.events.on(AsyncAuthHandler.EVENT_STREAM_FEATURES, self._on_stream_features)
        
        # Client config (para handshake)
        from ..config.bot_env import BotEnv
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

        # Cria ambiente de rede (sempre usa "direct" por padrão)
        network_env = NetworkEnv(NetworkEnv.TYPE_DIRECT)

        # Cria BotEnv que combina device_env e network_env
        self.bot_env = BotEnv(device_env, network_env)
        
        # Obtém MCC/MNC do número
        mcc, mnc = PhoneUtils.get_mcc_mnc(self.account_id)
        
        # Obtém platform ID correto para o ambiente
        platform_id = self.bot_env.deviceEnv.getPlatform()
        
        # Carrega ou gera fdid (phone_id) e expid (device_exp_id) do config usando profile
        self.config = await self.profile.config

        logger.debug(f"config: {self.config}")
        # Se device_config foi fornecido, usa ele; senão usa "android" como padrão
        device = self.config.device            

        if self.config.fdid is None:
            self.config.fdid = WATools.generatePhoneId(self.bot_env.deviceEnv)
            self.config.expid = WATools.generateDeviceId()
            await self.profile.write_config(self.config)     

        if self.config.device_name is not None:
            self.bot_env.deviceEnv.setOSName(self.config.os_name)
            self.bot_env.deviceEnv.setOSVersion(self.config.os_version)
            self.bot_env.deviceEnv.setManufacturer(self.config.manufacturer)
            self.bot_env.deviceEnv.setDeviceName(self.config.device_name)
            self.bot_env.deviceEnv.setDeviceModelType(self.config.device_model_type)
        else:
            self.config.os_name= self.bot_env.deviceEnv.getOSName()
            self.config.os_version = self.bot_env.deviceEnv.getOSVersion()
            self.config.manufacturer = self.bot_env.deviceEnv.getManufacturer()
            self.config.device_name = self.bot_env.deviceEnv.getDeviceName2()
            self.config.device_model_type = self.bot_env.deviceEnv.getDeviceModelType()

            await self.profile.write_config(self.config)


        cc = PhoneUtils.getMobileCC(self.account_id)
        lg,lc = PhoneUtils.getLGLC(cc)

        # Cria user agent com configuração do ambiente
        useragent = UserAgentConfig(
            platform=platform_id,
            app_version=AppVersionConfig(self.bot_env.deviceEnv.getVersion()),
            mcc=mcc or "724",
            mnc=mnc or "05",
            os_version=self.bot_env.deviceEnv.getOSVersion(),
            manufacturer=self.bot_env.deviceEnv.getManufacturer(),
            device=self.bot_env.deviceEnv.getDeviceName(),
            os_build_number=self.bot_env.deviceEnv.getBuildVersion(),
            phone_id=self.config.fdid,  # Usa fdid gerado ou do config
            locale_lang=lg,
            locale_country=lc,
            device_exp_id=base64.b64encode(self.config.expid).decode() if self.config.expid else "",  # Usa expid codificado em base64
            device_type=0,
            device_model_type=self.bot_env.deviceEnv.getDeviceModelType(),
        )
        
        # Obtém username do profile (preferencialmente) ou do account_id
        username = await self.profile.username if self.profile else None
        if not username:
            username = self.account_id.replace("+", "").replace("-", "").replace(" ", "")

        self.client_config = ClientConfig(
            username=int(username),
            passive=False,
            pushname="ZowPy",
            short_connect=True,  # Corrigido: deve ser True (igual zowsuplib)
            useragent=useragent,
        )
    
    async def _perform_handshake(self) -> None:
        """
        Executa handshake Noise seguindo o fluxograma.
        
        Fluxo:
        1. Verifica se existe profile (decide entre registro ou login)
        2. Carrega client_static_keypair do profile/config
        3. Carrega chaves (Identity, SignedPreKey, RegistrationId)
        4. Carrega chave RS remota se disponível
        5. Executa handshake IK (se RS existe) ou XX (se não existe)
        """
        import base64
        from ..noise.structs import KeyPair
        from dissononce.dh.x25519.public import PublicKey as DissononcePublicKey
        
        logger.info("Iniciando handshake Noise")
        
        # 1. Verifica se existe profile/account (decide entre registro ou login)
        
        if not  self.profile:
            error_msg = "profile not found, use import_account_from_six_parts to import the account first"
            logger.error(error_msg)

            await self.events.emit(AsyncAuthHandler.EVENT_FAILURE, {
                "reason": "Profile não encontrado - modo registro não implementado ainda",
                "message": error_msg,
                "code": "401"
            })
            
            raise RuntimeError(error_msg)


        local_static = self.config.client_static_keypair 

        logger.debug(f"local_static: {local_static}")

        if not local_static:           
            error_msg = "client_static_keypair not found"
            logger.error(error_msg)
            await self.events.emit(AsyncAuthHandler.EVENT_FAILURE, {
                "reason": "Local static keypair not found",
                "message": error_msg,
                "code": "401"
            })
            
            raise RuntimeError(error_msg)
        else:
            if type(local_static) is bytes:
                local_static = KeyPair.from_bytes(local_static)
            # assert type(local_static) is KeyPair, type(local_static)

        remote_static = self.config.server_static_public
        self._rs = remote_static
        

        # Converte para formato dissononce
        from dissononce.dh.keypair import KeyPair as DissononceKeyPair
        from dissononce.dh.private import PrivateKey as DissononcePrivateKey


        
        # O protocolo.start() executa o handshake internamente (IK ou XX)
        try:
            await self.noise_protocol.start(
                stream=self.stream,
                client_config=self.client_config,
                s=local_static,
                rs=remote_static,
                mode=None,  # Auto-detecta IK/XX baseado em rs
                deviceid=0
            )
            
            logger.info("Handshake concluído com sucesso")
            
            # Salva chave RS remota se foi recebida durante handshake
            if self.noise_protocol.rs:
                self.config.server_static_public = self.noise_protocol.rs 
                await self.profile.write_config(self.config)                
                logger.info("Chave RS remota salva para uso futuro")
            
            # NÃO envia <auth> após handshake - handshake Noise já autentica
            # Seguindo o fluxo do zowsuplib: servidor envia <success> diretamente (sem stream:features)
            logger.debug("Handshake concluído, aguardando <success> do servidor (handshake Noise já autentica)")
            
        except Exception as e:
            logger.error(f"Erro no handshake: {e}", exc_info=True)
            raise
    
    async def _check_profile_exists(self) -> bool:
        """
        Verifica se existe profile/account para a conta.
        Verifica se existe Account e ProfileConfig.
        
        Returns:
            bool: True se profile existe, False caso contrário
        """
        if not self.db_pool:
            return False
        
        try:
            from ..db.models import Account, ProfileConfig
            from sqlalchemy import select
            from ..utils.tools import StorageTools
            
            async with self.db_pool.get_session() as session:
                # Verifica se Account existe
                result = await session.execute(select(Account).filter_by(phone=self.account_id))
                account = result.scalar_one_or_none()
                
                if not account:
                    return False
                
                # Verifica se ProfileConfig existe
                result = await session.execute(
                    select(ProfileConfig).filter_by(
                        account_id=account.id,
                        name=StorageTools.NAME_CONFIG
                    )
                )
                profile_config = result.scalar_one_or_none()
                
                return profile_config is not None
        except Exception as e:
            logger.debug(f"Erro ao verificar profile: {e}")
            return False
    
    
    async def _build_client_payload(self) -> bytes:
        """Constrói ClientPayload para handshake."""
        from ..proto.client_payload import AsyncClientPayloadBuilder
        
        payload_bytes = await AsyncClientPayloadBuilder.build(
            client_config=self.client_config,
            session_id=int(time.time()),
            connect_reason="user_activated",
        )
        
        return payload_bytes
    
    async def _handle_tcp_message(self, message: bytes) -> None:
        """
        Handler de mensagem TCP socket.
        Processa segmentação: 3 bytes (tamanho big-endian) + dados
        
        Formato do protocolo WhatsApp:
        - 3 bytes: tamanho do segmento (big-endian, máximo 16MB - 1)
        - N bytes: dados do segmento
        
        NOTA: O header WA\x06\x03 é enviado pelo cliente e não é recebido do servidor.
        """
        if not self.stream:
            logger.warning("_handle_tcp_message: stream não disponível")
            return
        
        logger.debug(f"_handle_tcp_message: recebidos {len(message)} bytes do TCP")
        
        # Buffer para acumular dados e processar segmentação
        if not hasattr(self, '_tcp_read_buffer'):
            self._tcp_read_buffer = bytearray()
            logger.debug("_handle_tcp_message: buffer inicializado")
        
        self._tcp_read_buffer.extend(message)
        logger.debug(f"_handle_tcp_message: buffer agora tem {len(self._tcp_read_buffer)} bytes")
        
        # Processa segmentos completos
        segments_processed = 0
        try:
            while len(self._tcp_read_buffer) >= 3:
                # Lê tamanho (3 bytes big-endian)
                # Converte para int de 32 bits: adiciona byte 0 à esquerda
                size_bytes = bytes(self._tcp_read_buffer[:3])
                size = struct.unpack('>I', b"\x00" + size_bytes)[0]
                
                logger.debug(f"_handle_tcp_message: tamanho do segmento = {size} bytes (bytes: {size_bytes.hex()})")
                
                # Valida tamanho (máximo 16MB - 1)
                if size >= 16777216:
                    logger.error(f"Segmento muito grande: {size} bytes (máximo: 16777215)")
                    logger.error(f"Primeiros 20 bytes do buffer: {self._tcp_read_buffer[:20].hex()}")
                    self._tcp_read_buffer.clear()
                    return
                
                # Verifica se temos dados completos
                total_size = 3 + size
                if len(self._tcp_read_buffer) < total_size:
                    # Ainda não temos o segmento completo, aguarda mais dados
                    logger.debug(f"_handle_tcp_message: aguardando mais dados (temos {len(self._tcp_read_buffer)}, precisamos {total_size})")
                    break
                
                # Extrai segmento completo (sem os 3 bytes de tamanho)
                segment = bytes(self._tcp_read_buffer[3:total_size])
                self._tcp_read_buffer = self._tcp_read_buffer[total_size:]
                
                logger.info(f"_handle_tcp_message: segmento completo de {len(segment)} bytes extraído, adicionando ao stream")
                logger.debug(f"_handle_tcp_message: primeiros 50 bytes do segmento (hex): {segment[:50].hex() if len(segment) >= 50 else segment.hex()}")
                
                # Adiciona segmento ao stream para processamento
                await self.stream.put_read_segment(segment)
                segments_processed += 1
                logger.info(f"_handle_tcp_message: ✓ segmento de {len(segment)} bytes adicionado ao stream (total processados: {segments_processed})")
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem TCP: {e}", exc_info=True)
            logger.error(f"Buffer atual tem {len(self._tcp_read_buffer)} bytes")
            if len(self._tcp_read_buffer) > 0:
                logger.error(f"Primeiros 50 bytes do buffer (hex): {self._tcp_read_buffer[:50].hex()}")
            # Limpa buffer em caso de erro para evitar corrupção
            self._tcp_read_buffer.clear()
    
    async def _bridge_tcp_to_stream(self) -> None:
        """
        Bridge TCP Socket <-> Stream.
        
        Fluxo:
        - Recebe dados do TCP via _handle_tcp_message() → put_read_segment() → stream
        - Recebe dados do stream via get_write_segment() → segmenta → envia via TCP
        
        CRÍTICO: Este bridge DEVE estar rodando antes do handshake começar.
        """
        logger.info("Bridge TCP <-> Stream iniciado")
        try:
            while self._running:
                try:
                    # Obtém dados do stream para enviar via TCP
                    # Timeout de 1s para não bloquear indefinidamente
                    logger.debug("Bridge: aguardando dados do stream para enviar via TCP...")
                    data = await self.stream.get_write_segment(timeout=1.0)
                    
                    if not self.connection or not self.connection.is_connected():
                        logger.warning("Bridge: conexão não disponível, aguardando...")
                        await asyncio.sleep(0.5)
                        continue
                    
                    if not data:
                        logger.debug("Bridge: dados vazios, ignorando")
                        continue
                    
                    logger.info(f"Bridge: recebidos {len(data)} bytes do stream para enviar via TCP")
                    logger.debug(f"Bridge: primeiros 50 bytes (hex): {data[:50].hex() if len(data) >= 50 else data.hex()}")
                    
                    # Valida tamanho máximo (3 bytes = 16MB - 1)
                    if len(data) >= 16777216:
                        raise ValueError(f"Data too large to write; length={len(data)}")
                    
                    # Segmenta dados: 3 bytes (tamanho big-endian) + dados
                    # Formato: struct.pack('>I', len(data))[1:] + data
                    size_bytes = struct.pack('>I', len(data))[1:]
                    segment = size_bytes + data
                    logger.debug(f"Bridge: segmento preparado: {len(size_bytes)} bytes (tamanho) + {len(data)} bytes (dados) = {len(segment)} bytes total")
                    logger.debug(f"Bridge: bytes de tamanho (hex): {size_bytes.hex()}")
                    
                    await self.connection.send(segment)
                    logger.info(f"Bridge: ✓ enviados {len(data)} bytes via TCP (segmento total: {len(segment)} bytes)")
                    
                except asyncio.TimeoutError:
                    # Timeout normal - verifica se ainda está rodando
                    logger.debug("Bridge: timeout aguardando dados do stream (normal)")
                    if not self._running:
                        break
                    continue
                except StreamCancelledError:
                    logger.info("Bridge: stream cancelado, encerrando bridge")
                    break
                except Exception as e:
                    logger.error(f"Erro no bridge TCP->Stream: {e}", exc_info=True)
                    # Em caso de erro, aguarda um pouco antes de tentar novamente
                    await asyncio.sleep(0.1)
                    # Se conexão foi perdida, para o bridge
                    if not self.connection or not self.connection.is_connected():
                        logger.error("Bridge: conexão perdida, encerrando bridge")
                        break
        except asyncio.CancelledError:
            logger.debug("Bridge cancelado")
        finally:
            logger.info("Bridge TCP <-> Stream encerrado")
    
    async def _message_loop(self) -> None:
        """Loop de processamento de mensagens."""
        while self._running:
            try:
                # Processa mensagens mesmo antes de autenticação
                # (para processar stream:features, success, failure)
                if not self.noise_protocol:
                    await asyncio.sleep(0.5)
                    continue
                
                # Recebe mensagem descriptografada do transport
                decrypted = await self.noise_protocol.receive(timeout=1.0)
                if decrypted:
                    # Decodifica protocol node
                    node = await self.coder.receive_and_decode(decrypted)
                    if node:
                        # Processa node (inclui autenticação)
                        await self._process_protocol_node(node)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Erro no message loop: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_protocol_node(self, node: ProtocolNode) -> None:
        """Processa node do protocolo."""
        tag = node.tag
        
        try:
            # Valida estado do protocolo antes de processar
            if self.noise_protocol:
                protocol_state = getattr(self.noise_protocol, 'state', None)
                logger.debug(f"Processando node {tag} (protocol state: {protocol_state}, authenticated: {self._authenticated})")
            
            # Processa nodes de autenticação PRIMEIRO (sempre, mesmo sem autenticação)
            if tag == "stream:features":
                logger.info(f"Processando stream:features (authenticated={self._authenticated})")
                await self.auth_handler.handle_stream_features(node)
            elif tag == "success":
                # CRÍTICO: O servidor envia <success> diretamente após handshake (sem stream:features)
                # O handshake Noise já autentica, então <success> apenas confirma autenticação
                logger.info(f"Processando <success> do servidor (authenticated={self._authenticated})")
                await self.auth_handler.handle_success(node)
            elif tag == "failure":
                logger.error(f"Processando failure (authenticated={self._authenticated})")
                await self.auth_handler.handle_failure(node)
            elif tag == "stream:error":
                logger.error(f"Processando stream:error (authenticated={self._authenticated})")
                await self.auth_handler.handle_stream_error(node)
            elif tag == "challenge":
                # Trata challenge do servidor (se necessário)
                logger.info(f"Processando challenge (authenticated={self._authenticated})")
                await self._handle_challenge(node)
            # Processa outros nodes apenas se autenticado
            elif not self._authenticated:
                logger.debug(f"Node {tag} ignorado: não autenticado (aguardando autenticação)")
            elif tag == "message":
                await self.message_handler.handle_message(node)
            elif tag == "iq":
                await self._handle_iq(node)
            elif tag == "ack":
                await self.acks_handler.handle_ack(node)
            elif tag == "receipt":
                await self.receipts_handler.handle_receipt(node)
            elif tag == "presence":
                await self.presence_handler.handle_presence(node)
            elif tag == "notification":
                await self._handle_notification(node)
            else:
                logger.debug(f"Node não processado: {tag}")
                await self.events.emit("protocol:node", {"tag": tag, "node": node})
        
        except Exception as e:
            logger.error(f"Erro ao processar node {tag}: {e}", exc_info=True)
    
    async def _handle_iq(self, node: ProtocolNode) -> None:
        """Processa IQ adequadamente."""
        iq_type = node.get_attribute("type")
        iq_id = node.get_attribute("id")
        xmlns = node.get_attribute("xmlns")
        
        logger.debug(f"Processando IQ: type={iq_type}, id={iq_id}, xmlns={xmlns}")
        
        # Processa diferentes tipos de IQ
        if iq_type == "result":
            await self._handle_iq_result(node, iq_id, xmlns)
        elif iq_type == "error":
            await self._handle_iq_error(node, iq_id, xmlns)
        elif iq_type == "get":
            await self._handle_iq_get(node, iq_id, xmlns)
        elif iq_type == "set":
            await self._handle_iq_set(node, iq_id, xmlns)
        
        await self.events.emit("iq", {"node": node, "type": iq_type, "id": iq_id})
    
    async def _handle_iq_result(self, node: ProtocolNode, iq_id: str, xmlns: str) -> None:
        """Processa IQ result."""
        logger.debug(f"IQ result: id={iq_id}, xmlns={xmlns}")
        # Processa resultado específico baseado em xmlns
        # Por enquanto apenas loga
        pass
    
    async def _handle_iq_error(self, node: ProtocolNode, iq_id: str, xmlns: str) -> None:
        """Processa IQ error."""
        error_code = node.get_attribute("code")
        logger.warning(f"IQ error: id={iq_id}, xmlns={xmlns}, code={error_code}")
        await self.events.emit("iq:error", {"node": node, "id": iq_id, "code": error_code})
    
    async def _handle_iq_get(self, node: ProtocolNode, iq_id: str, xmlns: str) -> None:
        """Processa IQ get (requisição do servidor)."""
        logger.debug(f"IQ get: id={iq_id}, xmlns={xmlns}")
        # Por enquanto apenas loga
        # Pode precisar responder dependendo do xmlns
        pass
    
    async def _handle_iq_set(self, node: ProtocolNode, iq_id: str, xmlns: str) -> None:
        """Processa IQ set (comando do servidor)."""
        logger.debug(f"IQ set: id={iq_id}, xmlns={xmlns}")
        # Processa comando específico baseado em xmlns
        # Por enquanto apenas loga
        pass
    
    async def _handle_notification(self, node: ProtocolNode) -> None:
        """Processa notificação."""
        await self.events.emit("notification", {"node": node})
    
    async def _keepalive_loop(self) -> None:
        """Loop de keepalive para manter conexão online."""
        while self._running:
            try:
                # Aguarda 30 segundos
                await asyncio.sleep(30)
                
                if self._connected and self._authenticated:
                    # Envia ping/keepalive
                    await self._send_keepalive()
            
            except Exception as e:
                logger.error(f"Erro no keepalive: {e}")
    
    async def _send_keepalive(self) -> None:
        """Envia mensagem de keepalive."""
        # Cria node de keepalive
        keepalive_node = ProtocolNode(
            tag="iq",
            attributes={
                "id": f"keepalive_{int(time.time())}",
                "type": "get",
                "xmlns": "w:p",
            }
        )
        
        await self._send_protocol_node(keepalive_node)
    
    async def send_text(
        self,
        to: str,
        text: str,
        message_id: Optional[str] = None
    ) -> str:
        """
        Envia mensagem de texto.
        
        :param to: JID do destinatário
        :param text: Texto da mensagem
        :param message_id: ID da mensagem (opcional, será gerado se não fornecido)
        :return: ID da mensagem enviada
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        # Normaliza JID
        to_jid = to_whatsapp_jid(to)
        
        # Gera message ID se não fornecido
        if not message_id:
            message_id = f"{int(time.time() * 1000)}-{self.account_id}"
        
        # Cria node de mensagem
        message_node = ProtocolNode(
            tag="message",
            attributes={
                "to": to_jid,
                "id": message_id,
                "type": "text",
            },
            children=[
                ProtocolNode(
                    tag="body",
                    data=text.encode('utf-8')
                )
            ]
        )
        
        # Envia mensagem
        await self._send_protocol_node(message_node)
        
        logger.info(f"Mensagem enviada para {to_jid}: {text[:50]}...")
        
        return message_id
    
    async def _send_protocol_node(self, node: ProtocolNode) -> None:
        """
        Envia protocol node.
        
        :param node: Node do protocolo
        """
        # Validações
        if not self.noise_protocol:
            raise RuntimeError("Noise protocol não disponível")
        
        # Nodes de autenticação podem ser enviados antes de estar autenticado
        auth_nodes = ["auth", "challenge", "response"]
        is_auth_node = node.tag in auth_nodes
        
        if not is_auth_node and not self._authenticated:
            raise RuntimeError(f"Não é possível enviar node {node.tag}: não autenticado")
        
        # Valida estado do protocolo
        protocol_state = getattr(self.noise_protocol, 'state', None)
        # Compara com enum ou string
        state_value = protocol_state.value if hasattr(protocol_state, 'value') else str(protocol_state) if protocol_state else None
        if state_value != "transport":
            logger.warning(f"Enviando node {node.tag} mas protocolo não está em TRANSPORT (estado: {state_value})")
            # Para nodes de auth, pode estar transitando, então não falha
        
        logger.debug(f"Enviando protocol node: tag={node.tag}, authenticated={self._authenticated}, state={protocol_state}")
        
        # Codifica node
        encoded = await self.coder.encode_and_send(node)
        
        # Obtém dados codificados do evento
        # Por enquanto, usa encoder diretamente
        encoded_bytes = await self.coder.encoder.encode(node)
        
        # Envia via noise protocol (criptografa e envia)
        await self.noise_protocol.send(encoded_bytes)
        
        logger.debug(f"Node {node.tag} enviado com sucesso")
    
    async def disconnect(self) -> None:
        """Desconecta de forma assíncrona."""
        logger.info("Desconectando...")
        
        self._running = False
        self._connected = False
        self._authenticated = False
        
        # Cancela stream primeiro (para desbloquear qualquer operação pendente)
        if self.stream:
            try:
                await self.stream.cancel()
                logger.debug("Stream cancelado")
            except Exception as e:
                logger.debug(f"Erro ao cancelar stream: {e}")
        
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
        
        # Aguarda tasks terminarem (apenas se houver tasks)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Desconecta conexão
        if self.connection:
            try:
                await self.connection.disconnect()
            except Exception as e:
                logger.debug(f"Erro ao desconectar: {e}")
        
        # Fecha axolotl manager (store)
        if self.axolotl_manager and hasattr(self.axolotl_manager, '_store'):
            try:
                self.axolotl_manager._store.close()
            except Exception as e:
                logger.debug(f"Erro ao fechar store: {e}")
        
        await self.events.emit("disconnected")
        logger.info("Desconectado")
    
    async def _on_tcp_connected(self) -> None:
        """
        Handler para EVENT_STATE_CONNECTED (conexão TCP estabelecida).
        
        Seguindo o fluxo do zowsuplib:
        - YowNetworkLayer.onConnected() → emite EVENT_STATE_CONNECTED
        - YowAuthenticationProtocolLayer.on_connected() → emite EVENT_AUTH
        - AxolotlControlLayer.on_connected() → chama level_prekeys()
        """
        logger.info("EVENT_STATE_CONNECTED: Conexão TCP estabelecida")
        
        # 1. Gera prekeys (equivalente a AxolotlControlLayer.on_connected())
        if self.axolotl_manager:
            try:
                logger.info("Gerando prekeys após conexão TCP estabelecida...")
                prekeys = await self.axolotl_manager.level_prekeys()
                if prekeys:
                    logger.info(f"Geradas {len(prekeys)} prekeys com sucesso")
                else:
                    logger.info("Prekeys já existem em quantidade suficiente (não foi necessário gerar)")
            except Exception as e:
                logger.warning(f"Erro ao gerar prekeys (não crítico): {e}")
        
        # 2. Emite EVENT_AUTH (equivalente a YowAuthenticationProtocolLayer.on_connected())
        # Isso iniciará o handshake quando o handler _on_auth for chamado
        logger.info("Emitindo EVENT_AUTH para iniciar handshake")
        await self.events.emit(AsyncAuthHandler.EVENT_AUTH, {})
    
    async def _on_auth(self, data: Dict[str, Any]) -> None:
        """
        Handler para EVENT_AUTH (inicia handshake).
        
        Seguindo o fluxo do zowsuplib:
        - YowNoiseLayer.on_auth() recebe EVENT_AUTH
        - Inicia handshake (IK ou XX)
        """
        logger.info("EVENT_AUTH recebido, iniciando handshake...")
        
        # Verifica se já está em handshake
        if hasattr(self, '_handshake_in_progress') and self._handshake_in_progress:
            logger.warning("Handshake já em progresso, ignorando EVENT_AUTH duplicado")
            return
        
        # Marca handshake como em progresso
        self._handshake_in_progress = True
        
        try:
            # Executa handshake
            await self._perform_handshake()
            logger.info("Handshake concluído com sucesso")
        except Exception as e:
            logger.exception(e)
            logger.error(f"Erro no handshake: {e}", exc_info=True)
            self._handshake_in_progress = False
            raise
        finally:
            self._handshake_in_progress = False
    
    
    async def _on_handshake_complete(self) -> None:
        """
        Callback quando handshake é concluído com sucesso.
        Emite EVENT_AUTHED para indicar que o handshake terminou.
        """
        logger.info("Handshake concluído com sucesso, emitindo EVENT_AUTHED")

        # Salva chave RS remota se foi recebida durante handshake
        if self.noise_protocol and self.noise_protocol.rs:
            try:
                import base64
                rs_data = self.noise_protocol.rs.data
                await self.state_store.set("noise_remote_static", base64.b64encode(rs_data).decode())
                logger.info("Chave RS remota salva para uso futuro")
            except Exception as e:
                logger.warning(f"Erro ao salvar chave RS: {e}")

        # Emite EVENT_AUTHED
        await self.events.emit(AsyncAuthHandler.EVENT_AUTHED, {
            "handshake_completed": True
        })
    
    async def _wait_for_authentication(self) -> None:
        """Aguarda autenticação ser concluída."""
        await self._auth_event.wait()
        if self._auth_failed:
            raise RuntimeError("Autenticação falhou")
    
    async def _on_authenticated(self, data: Dict[str, Any]) -> None:
        """
        Callback quando EVENT_AUTHED é emitido.
        
        Seguindo o fluxo do zowsuplib:
        - YowNoiseLayer.on_handshake_finished() → emite EVENT_AUTHED
        - YowAuthenticationProtocolLayer.on_authed() → pode enviar auth (mas não é necessário)
        - Aguarda <success> do servidor
        - SendLayer.onSuccess() → marca como autenticado
        
        NOTA: No zowpy, este handler é chamado em dois momentos:
        1. Após handshake concluído (EVENT_AUTHED emitido por _on_handshake_complete)
        2. Quando <success> é recebido (EVENT_AUTHED emitido por auth_handler.handle_success)
        
        Apenas quando <success> é recebido é que marcamos como autenticado.
        """
        node = data.get("node")
        handshake_completed = data.get("handshake_completed", False)
        
        if handshake_completed:
            # EVENT_AUTHED emitido após handshake concluído
            # Aguarda <success> do servidor (não marca como autenticado ainda)
            logger.info("EVENT_AUTHED recebido após handshake concluído, aguardando <success> do servidor")
            # Não marca como autenticado ainda - aguarda <success>
            return
        
        # EVENT_AUTHED emitido quando <success> é recebido
        logger.info("Autenticação bem-sucedida (<success> recebido)")
        
        # Valida estado antes de marcar como autenticado
        if self.noise_protocol:
            protocol_state = getattr(self.noise_protocol, 'state', None)
            if protocol_state != 'TRANSPORT':
                logger.warning(f"Marcando como autenticado mas protocolo não está em TRANSPORT (estado: {protocol_state})")
        
        self._authenticated = True
        self._auth_failed = False
        self._auth_event.set()
        
        logger.info(f"Cliente autenticado: account_id={self.account_id}, authenticated={self._authenticated}")
        
        # Atualiza Account no banco de dados (marca como logado)
        if self.db_pool:
            try:
                from ..db.models import Account
                from sqlalchemy import select
                async with self.db_pool.get_session() as session:
                    result = await session.execute(select(Account).filter_by(phone=self.account_id))
                    account = result.scalar_one_or_none()
                    if account:
                        account.is_logged_in = True
                        account.is_initialized = True
                        # Atualiza pushname se disponível no profile config
                        if self._profile:
                            config = await self._profile.config
                            if config and config.pushname:
                                account.pushname = config.pushname
                        await session.commit()
                        logger.debug(f"Account {self.account_id} marcado como logado no banco")
                    else:
                        logger.warning(f"Account {self.account_id} não encontrado no banco para atualizar status")
            except Exception as e:
                logger.warning(f"Erro ao atualizar status de login no banco: {e}", exc_info=True)
        
        # Envia presence (available) após autenticação
        await self._send_initial_presence()
    
    async def _on_auth_failure(self, data: Dict[str, Any]) -> None:
        """Callback quando autenticação falha."""
        error_code = data.get("code")
        node = data.get("node")
        
        logger.error(f"Falha na autenticação (code: {error_code})")
        
        # Log detalhado do erro
        if node:
            logger.error(f"Failure node: tag={node.tag}, attributes={getattr(node, 'attributes', {})}")
        
        self._auth_failed = True
        self._authenticated = False
        self._auth_event.set()
        
        # Emite evento de falha
        await self.events.emit("auth:failed", {
            "code": error_code,
            "node": node,
            "account_id": self.account_id
        })
    
    async def _on_stream_features(self, data: Dict[str, Any]) -> None:
        """
        Callback quando recebe stream:features.
        
        NOTA: Baseado nos logs do zowsuplib, o servidor NÃO envia stream:features após handshake.
        O servidor envia <success> diretamente. Este handler é mantido apenas para compatibilidade
        caso o servidor envie stream:features em algum cenário específico.
        """
        node = data.get("node")
        if not node:
            logger.warning("stream:features recebido sem node")
            return
        
        # Extrai features do node
        features = []
        if hasattr(node, 'children'):
            features = [child.tag for child in node.children]
        elif hasattr(node, 'get_children'):
            features = [child.tag for child in node.get_children()]
        
        logger.info(f"Recebido stream:features com features: {features} (não esperado após handshake Noise)")
        
        # NOTA: Baseado nos logs do zowsuplib, o servidor NÃO envia stream:features após handshake
        # O servidor envia <success> diretamente. Não enviamos <auth> porque o handshake Noise já autentica.
        # Se stream:features for recebido, apenas loga (pode ser um caso especial)
        logger.debug("stream:features recebido, mas não é necessário enviar <auth> (handshake Noise já autentica)")
    
    async def _send_auth_credentials(self) -> None:
        """Envia credenciais de autenticação no formato correto."""
        try:
            # Valida estado do protocolo
            if not self.noise_protocol:
                raise RuntimeError("Noise protocol não disponível")
            
            protocol_state = getattr(self.noise_protocol, 'state', None)
            if protocol_state != 'TRANSPORT':
                logger.warning(f"Enviando auth em estado não TRANSPORT: {protocol_state}")
            
            # Obtém username (número de telefone sem formatação)
            username = await self.state_store.get_username()
            if not username:
                # Usa profile.username ou account_id como username (remove formatação)
                username = await self._profile.username if self._profile else None
                if not username:
                    username = self.account_id.replace("+", "").replace("-", "").replace(" ", "")
            
            # Após Noise handshake, o WhatsApp usa WAUTH-2 sem password tradicional
            # O nonce pode ser vazio ou derivado do handshake
            # Formato correto baseado em AuthProtocolEntity do zowsuplib
            auth_node = ProtocolNode(
                tag="auth",
                attributes={
                    "mechanism": "WAUTH-2",  # Formato correto (não "WA_AUTH_MECHANISM")
                    "user": username,
                    "passive": "false",  # Não é conexão passiva
                },
                data=None  # Após Noise handshake, não precisa de password/nonce no data
            )
            
            logger.info(f"Enviando <auth> com mechanism=WAUTH-2, user={username}")
            logger.debug(f"Auth node: tag={auth_node.tag}, attributes={auth_node.attributes}, data={auth_node.data}")
            
            # Envia node
            await self._send_protocol_node(auth_node)
            
        except Exception as e:
            logger.error(f"Erro ao enviar credenciais: {e}", exc_info=True)
            self._auth_failed = True
            self._auth_event.set()
            raise
    
    async def _send_initial_presence(self) -> None:
        """Envia presence inicial após autenticação."""
        try:
            # Valida que está autenticado antes de enviar presence
            if not self._authenticated:
                logger.warning("Tentativa de enviar presence sem estar autenticado")
                return
            
            presence_node = ProtocolNode(
                tag="presence",
                attributes={
                    "type": "available",
                }
            )
            await self._send_protocol_node(presence_node)
            logger.info("Presence (available) enviado após autenticação")
        except Exception as e:
            logger.error(f"Erro ao enviar presence inicial: {e}", exc_info=True)
    
    async def _handle_challenge(self, node: ProtocolNode) -> None:
        """Trata challenge do servidor (se necessário)."""
        try:
            # O servidor pode enviar um challenge que precisa ser respondido
            challenge_data = node.data if hasattr(node, 'data') else None
            logger.info(f"Challenge recebido: {len(challenge_data) if challenge_data else 0} bytes")
            
            # Por enquanto, apenas loga
            # Se necessário, implementar resposta ao challenge
            # A resposta geralmente envolve derivar uma resposta do challenge usando as chaves do handshake
            
            await self.events.emit("auth:challenge", {"node": node, "data": challenge_data})
        except Exception as e:
            logger.error(f"Erro ao processar challenge: {e}", exc_info=True)
    
    def is_connected(self) -> bool:
        """Verifica se está conectado."""
        return self._connected and self._authenticated
    
    @staticmethod
    async def import_account_from_six_parts(
        six_parts_data: str,
        *,
        env: str = "android",
        db_pool=None,
    ) -> str:
        """
        Importa uma conta nova a partir de uma string no formato 6-parts.
        
        Args:
            six_parts_data: String com 6 campos separados por vírgula (phone,pk1,sk1,pk2,sk2,sixth)
            env: Ambiente do dispositivo (default: "android")
            db_pool: Pool de banco de dados (opcional)
        
        Returns:
            str: Número de telefone (account_id) da conta importada
        """
        return await import_account_from_six_parts(
            six_parts_data,
            env=env,
            db_pool=db_pool
        )

