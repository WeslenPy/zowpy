"""
ZowPy Client - API pública moderna e limpa.

Wrapper sobre WhatsAppClient.
Estilo whatsmeow: wait_for_message com filtros e condições.
"""

import asyncio
from typing import Optional, Callable, Dict, Any, Union
from loguru import logger

from ..core.client import WhatsAppClient
from ..core.events import AsyncEventEmitter
from ..core.store import AsyncStateStore
from ..axolotl.sessioncipher import SessionCipher
from ..protocol.messages import AsyncMessageHandler
from ..db.pool import AsyncDatabasePool
from .errors import ZowPyError, ConnectionError


class ZowPyClient:
    """
    API pública moderna e limpa.
    Wrapper sobre WhatsAppClient.
    """
    
    def __init__(
        self,
        account_id: str,
        db_pool: Optional[AsyncDatabasePool] = None,
        device_env: Optional[str] = None,
    ):
        """
        Inicializa cliente ZowPy.
        
        Args:
            account_id: ID da conta (número de telefone)
            db_pool: Pool de banco de dados (opcional)
            device_env: Ambiente do dispositivo (android, ios, smb_android, smb_ios)
        """
        self.account_id = account_id
        from ..config.settings import settings
        self.db_pool = db_pool or AsyncDatabasePool(settings.zowpy_db_url)
        self.device_env = device_env or "smb_android"
        
        # Componentes internos
        self._state_store: Optional[AsyncStateStore] = None
        self._session_cipher: Optional[SessionCipher] = None
        self._message_handler: Optional[AsyncMessageHandler] = None
        self._client: Optional[WhatsAppClient] = None
        
        # Eventos
        self._events = AsyncEventEmitter()
    
    async def connect(self) -> None:
        """
        Conecta de forma totalmente assíncrona.
        
        Raises:
            ConnectionError: Se conexão falhar
        """
        try:
            # Inicializa DB pool se necessário
            if not hasattr(self.db_pool, '_pool') or self.db_pool._pool is None:
                await self.db_pool.initialize()
            
            # Inicializa banco de dados (cria tabelas se não existirem)
            from ..db import init_db
            await init_db(db_pool=self.db_pool)
            
            # Cria cliente completo
            # Endpoint TCP para WhatsApp (não WebSocket)
            endpoint = ("e8.whatsapp.net", 5222)
            self._client = WhatsAppClient(
                self.account_id,
                endpoint,
                self.db_pool,
                device_config=self.device_env,
            )
            
            # Conecta eventos do cliente aos eventos públicos
            self._client.events.on("connected", lambda *args, **kwargs: self._events.emit("connected", *args, **kwargs))
            self._client.events.on("disconnected", lambda *args, **kwargs: self._events.emit("disconnected", *args, **kwargs))
            self._client.events.on("message", lambda msg: self._events.emit("message", msg))
            self._client.events.on("connection:error", lambda err: self._events.emit("connection:error", err))
            
            # Conecta - await, não bloqueia
            await self._client.connect()
            
            logger.info(f"Cliente {self.account_id} conectado")
            
        except Exception as e:
            raise ConnectionError(f"Erro ao conectar: {e}") from e
    
    async def send_text(self, to: str, text: str) -> str:
        """
        Envia mensagem de texto de forma totalmente assíncrona.
        
        Args:
            to: JID do destinatário (número de telefone ou JID completo)
            text: Texto da mensagem
        
        Returns:
            ID da mensagem enviada
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        # Envia mensagem via cliente
        message_id = await self._client.send_text(to, text)
        
        return message_id
    
    async def wait_for_message(
        self,
        timeout: Optional[float] = None,
        from_jid: Optional[str] = None,
        message_type: Optional[str] = None,
        condition: Optional[Callable[[dict], bool]] = None,
    ) -> dict:
        """
        Aguarda mensagem de forma totalmente assíncrona.
        Estilo whatsmeow: suporta filtros e condições.
        
        Args:
            timeout: Timeout em segundos (None = sem timeout)
            from_jid: Filtrar por JID do remetente (opcional)
            message_type: Filtrar por tipo de mensagem (opcional)
            condition: Função customizada para filtrar mensagens (opcional)
        
        Returns:
            dict: Mensagem recebida que atende aos filtros
        
        Raises:
            ZowPyError: Se timeout ou erro ocorrer
        
        Example:
            # Aguarda qualquer mensagem
            msg = await client.wait_for_message(timeout=30.0)
            
            # Aguarda mensagem de um remetente específico
            msg = await client.wait_for_message(
                timeout=30.0,
                from_jid="5511999999999@s.whatsapp.net"
            )
            
            # Aguarda mensagem de texto
            msg = await client.wait_for_message(
                timeout=30.0,
                message_type="text"
            )
            
            # Aguarda mensagem com condição customizada
            msg = await client.wait_for_message(
                timeout=30.0,
                condition=lambda m: "hello" in m.get("text", "").lower()
            )
        """
        def message_condition(*args, **kwargs):
            """Condição para filtrar mensagens"""
            if not args:
                return False
            
            message = args[0] if isinstance(args[0], dict) else {}
            
            # Filtro por remetente
            if from_jid is not None:
                msg_from = message.get("from") or message.get("jid")
                if msg_from != from_jid and not msg_from.endswith(from_jid):
                    return False
            
            # Filtro por tipo
            if message_type is not None:
                msg_type = message.get("type") or message.get("message_type")
                if msg_type != message_type:
                    return False
            
            # Condição customizada
            if condition is not None:
                if not condition(message):
                    return False
            
            return True
        
        try:
            args, kwargs = await self._events.wait_for(
                "message",
                timeout=timeout,
                condition=message_condition
            )
            return args[0] if args else {}
        except Exception as e:
            from ..core.events import EventTimeoutError
            if isinstance(e, EventTimeoutError):
                raise ZowPyError(f"Timeout aguardando mensagem: {e}") from e
            raise ZowPyError(f"Erro ao aguardar mensagem: {e}") from e
    
    async def disconnect(self) -> None:
        """Desconecta de forma assíncrona"""
        if self._client:
            await self._client.disconnect()
        
        if self.db_pool:
            await self.db_pool.close()
    
    def on_message(self, handler: Callable) -> None:
        """Registra handler de mensagem"""
        self._events.on("message", handler)
    
    def on_connected(self, handler: Callable) -> None:
        """Registra handler de conexão"""
        self._events.on("connected", handler)
    
    def on_disconnected(self, handler: Callable) -> None:
        """Registra handler de desconexão"""
        self._events.on("disconnected", handler)


