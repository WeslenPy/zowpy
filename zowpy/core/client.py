"""
WhatsApp Client V2 - Cliente com fluxo linear assíncrono.

Baseado no zowsuplib, mas totalmente assíncrono e sem eventos complexos.
Fluxo direto: conexão → handshake → autenticação.
"""

import asyncio
import base64
import time
from typing import Optional, Dict, Any, Tuple
from loguru import logger

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
        endpoint: Tuple[str, int] = ("e15.whatsapp.net", 5222),
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
        self.endpoint = endpoint
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
        
        # Stores e handlers
        self.state_store: Optional[AsyncStateStore] = None
        self.message_handler: Optional[AsyncMessageHandler] = None
        self.acks_handler: Optional[AsyncAcksHandler] = None
        self.receipts_handler: Optional[AsyncReceiptHandler] = None
        self.presence_handler: Optional[AsyncPresenceHandler] = None
        self.auth_handler: Optional[AsyncAuthHandler] = None
        
        # Config
        self.profile: Optional[AsyncProfile] = None
        self.config: Optional[Config] = None
        self.bot_env: Optional[BotEnv] = None
        self.client_config: Optional[ClientConfig] = None
        
        # Estado
        self._running = False
        self._connected = False
        self._authenticated = False
        
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
            
            # 2. Conecta TCP socket
            logger.info("Conectando TCP socket...")
            self.connection = AsyncConnection(self.endpoint, proxy=self.proxy)
            await self.connection.connect()
            logger.info("✓ TCP socket conectado")
            
            # 3. Envia header WA\x06\x03
            logger.info("Enviando header WA\\x06\\x03...")
            await self.connection.send_header()
            logger.info("✓ Header enviado")
            
            # 4. Carrega/gera prekeys (equivalente a AxolotlControlLayer.on_connected())
            logger.info("Carregando/gerando prekeys...")
            await self._load_prekeys()
            logger.info("✓ Prekeys carregados")
            
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
            
            # 8. Aguarda <success> do servidor
            logger.info("Aguardando confirmação do servidor (<success>)...")
            await self._wait_for_success()
            logger.info("✓ Autenticado com sucesso")
            
            # 9. Inicia loops de processamento
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
        
        # Handlers (sem eventos - versão simplificada)
        self.message_handler = AsyncMessageHandler(events)
        self.acks_handler = AsyncAcksHandler(events)
        self.receipts_handler = AsyncReceiptHandler(events)
        self.presence_handler = AsyncPresenceHandler(events)
        self.auth_handler = AsyncAuthHandler(events)
        
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
    
    async def _wait_for_success(self, timeout: float = 30.0) -> None:
        """
        Aguarda <success> do servidor de forma linear.
        
        Baseado no zowsuplib:
        - Servidor envia <success> diretamente após handshake (sem stream:features)
        - Processa mensagens até receber <success>
        
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
                error_code = node.get_attribute("code", "unknown")
                logger.error(f"<failure> recebido: code={error_code}")
                raise AuthenticationError(f"Login falhou: code={error_code}")
            elif node.tag == "stream:features":
                logger.info("stream:features recebido (não esperado após handshake, mas ignorando)")
                # Não é esperado após handshake, mas não é erro
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
                
                # Processa node (passa dados brutos para handlers que precisam)
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
        """Processa node do protocolo."""
        tag = node.tag
        
        try:
            if tag == "message":
                # Se temos dados brutos, passa para o handler (espera bytes)
                if raw_data:
                    await self.message_handler.handle_message(raw_data, from_jid=node.get_attribute("from"))
                else:
                    # Se não temos dados brutos, apenas emite evento com dados do node
                    body_child = node.get_child("body")
                    message_data = {
                        "from": node.get_attribute("from"),
                        "text": body_child.data.decode('utf-8') if body_child and body_child.data else "",
                        "type": node.get_attribute("type"),
                        "id": node.get_attribute("id"),
                    }
                    await self.events.emit("message", message_data)
            elif tag == "ack":
                await self.acks_handler.handle_ack(node)
            elif tag == "receipt":
                await self.receipts_handler.handle_receipt(node)
            elif tag == "presence":
                await self.presence_handler.handle_presence(node)
            elif tag == "iq":
                await self._handle_iq(node)
            else:
                logger.debug(f"Node não processado: {tag}")
        
        except Exception as e:
            logger.error(f"Erro ao processar node {tag}: {e}", exc_info=True)
    
    async def _handle_iq(self, node: ProtocolNode) -> None:
        """Processa IQ."""
        logger.debug(f"Processando IQ: {node.get_attribute('type')}")
        # Por enquanto apenas loga
    
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
    
    async def _send_protocol_node(self, node: ProtocolNode) -> None:
        """Envia protocol node."""
        if not self.transport:
            raise RuntimeError("Transport não disponível")
        
        # Codifica node
        encoded_bytes = await self.coder.encoder.encode(node)
        
        # Envia via transport (criptografa e envia)
        await self.transport.send(encoded_bytes)
    
    async def send_text(
        self,
        to: str,
        text: str,
        message_id: Optional[str] = None
    ) -> str:
        """Envia mensagem de texto."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        
        to_jid = to_whatsapp_jid(to)
        
        if not message_id:
            message_id = f"{int(time.time() * 1000)}-{self.account_id}"
        
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
        
        await self._send_protocol_node(message_node)
        logger.info(f"Mensagem enviada para {to_jid}: {text[:50]}...")
        
        return message_id
    
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

