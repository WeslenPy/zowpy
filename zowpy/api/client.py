"""
ZowPy Client - API pública moderna e limpa.

Wrapper sobre WhatsAppClient.
Estilo whatsmeow: wait_for_message com filtros e condições.
"""

import asyncio
import random
from typing import Optional, Callable, Dict, Any, Union
from loguru import logger

from zowpy.config.network import ProxyConfig
from zowpy.db.config.engine import AsyncSessionMaker

from ..core.client import MediaType, WhatsAppClient
from ..core.events import AsyncEventEmitter
from ..core.handlers.profile_response import ProfileResponse
from ..core.store import AsyncStateStore
from ..axolotl.sessioncipher import SessionCipher
from ..protocol.messages import AsyncMessageHandler
from .errors import ZowPyError, ConnectionError


class ZowPyClient:
    """
    API pública moderna e limpa.
    Wrapper sobre WhatsAppClient.
    """
    
    def __init__(
        self,
        account_id: str,
        session_maker: Optional[AsyncSessionMaker] = None,
        env: Optional[str] = None,
    ):
        """
        Inicializa cliente ZowPy.
        
        Args:
            account_id: ID da conta (número de telefone)
            session_maker: Pool de banco de dados (opcional)
            env: Ambiente do dispositivo (android, ios, smb_android, smb_ios)
        """
        self.account_id = account_id
        from ..config.settings import settings
        self.session_maker = session_maker or AsyncSessionMaker
        self.env = env
        
        # Componentes internos
        self._session_cipher: Optional[SessionCipher] = None
        self._message_handler: Optional[AsyncMessageHandler] = None
        self._client: Optional[WhatsAppClient] = None

        self.proxy: Optional[ProxyConfig] = None
        
        # Eventos
        self._events = AsyncEventEmitter()



    @staticmethod
    async def get_account_active():
        return await WhatsAppClient.get_account_active()


    @staticmethod
    async def get_all_accounts_active():
        return await WhatsAppClient.get_all_accounts_active()


    
    
    async def connect(self) -> None:
        """
        Conecta de forma totalmente assíncrona.
        
        Raises:
            ConnectionError: Se conexão falhar
        """
        try:
            
            from ..db.config import create_db
            await create_db()
            
            # Cria cliente completo
            self._client = WhatsAppClient(
                self.account_id,
                session_maker=self.session_maker,
                env=self.env,
                proxy=self.proxy,
            )
            
            # Conecta eventos do cliente aos eventos públicos
            async def forward_connected(*args, **kwargs):
                event_data = args[0] if args else kwargs
                await self._events.emit("connected", event_data)
            
            async def forward_disconnected(*args, **kwargs):
                event_data = args[0] if args else kwargs
                await self._events.emit("disconnected", event_data)
            
            async def forward_message(*args, **kwargs):
                message_data = args[0] if args else kwargs
                await self._events.emit("message", message_data)
            
            async def forward_connection_error(*args, **kwargs):
                error_data = args[0] if args else kwargs
                await self._events.emit("connection:error", error_data)
            
            self._client.events.on("connected", forward_connected)
            self._client.events.on("disconnected", forward_disconnected)
            self._client.events.on("message", forward_message)
            self._client.events.on("connection:error", forward_connection_error)
            
            await self._client.connect()
            
            logger.info(f"Cliente {self.account_id} conectado")
            
        except Exception as e:
            raise ConnectionError(f"Erro ao conectar: {e}") from e



    def _generate_random_text_color(self) -> int:
        """
        Gera uma cor aleatória para texto no formato ARGB (uint32).

        Returns:
            int: Cor ARGB no formato uint32 (0 a 4294967295)
                 Alpha=255 (opaco), R/G/B aleatórios
        """
        # Alpha sempre 255 (opaco), R/G/B aleatórios
        alpha = 255
        red = random.randint(0, 255)
        green = random.randint(0, 255)
        blue = random.randint(0, 255)

        # Formato ARGB: (A << 24) | (R << 16) | (G << 8) | B
        # Garante que o valor está no range uint32 (0 a 4294967295)
        argb_value = (alpha << 24) | (red << 16) | (green << 8) | blue
        
        # Garante que está dentro do range uint32
        # Máximo: 0xFFFFFFFF = 4294967295
        return argb_value & 0xFFFFFFFF

    def _generate_random_background_color(self) -> int:
        """
        Gera uma cor aleatória para fundo no formato ARGB (uint32).

        Returns:
            int: Cor ARGB no formato uint32 (0 a 4294967295)
                 com alpha variável para transparência
        """
        # Alpha variável (semi-transparente a opaco)
        alpha = random.randint(200, 255)  # 200-255 para boa visibilidade
        red = random.randint(0, 255)
        green = random.randint(0, 255)
        blue = random.randint(0, 255)

        # Formato ARGB: (A << 24) | (R << 16) | (G << 8) | B
        # Garante que o valor está no range uint32 (0 a 4294967295)
        argb_value = (alpha << 24) | (red << 16) | (green << 8) | blue
        
        return argb_value & 0xFFFFFFFF # Garante que está dentro do range uint32


    async def get_user_info(self, jid: str) -> ProfileResponse:
        """Obtém informações do usuário. Retorna ProfileResponse."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        return await self._client.profile_handler.get_user_info(jid)

    async def set_description_business(self, description: str) -> ProfileResponse:
        """Define a descrição do perfil business. Retorna ProfileResponse."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        return await self._client.profile_handler.set_description_business(description)

    async def get_business_profile(self, jid: str) -> ProfileResponse:
        """Obtém o perfil business. Retorna ProfileResponse."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        return await self._client.profile_handler.get_business_profile(jid)

    async def get_account_info(self) -> ProfileResponse:
        """Obtém informações da conta (creation, last_reg). Retorna ProfileResponse."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        return await self._client.profile_handler.get_account_info()


    async def set_2fa():pass

    async def set_business_name(self, name: str) -> ProfileResponse:
        """Define o nome de negócio verificado (conta business / SMB). Retorna ProfileResponse."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        return await self._client.profile_handler.set_business_name(name)

    async def set_profile_name(self, name: str) -> ProfileResponse:
        """Define o nome da conta (pushname). Retorna ProfileResponse."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        return await self._client.profile_handler.set_profile_name(name)

    # async def 

    async def delete_message(self,to:str,message_id:str):

        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        # Envia mensagem via cliente
        message_id = await self._client.delete_message(to=to, message_id=message_id)
        
        return message_id

    async def edit_message(self,text:str,to:str,message_id:str):

        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        # Envia mensagem via cliente
        message_id = await self._client.edit_message(to=to, text=text, message_id=message_id)
        
        return message_id


    async def send_status(        
        self,
        media_type:MediaType,
        text:Optional[str]=None,
        file_path_or_url:Optional[str]=None,
        text_color:Optional[str]= None,
        background_color:Optional[str] = None,
        font:Optional[int] = None,
        caption:Optional[str] = None,
        preview_type:Optional[int] = None,):
        """
        Envio de status para contatos cadastrados
        """

        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")

        message_id=  await self._client.send_status(
            media_type=media_type,
            text=text,
            file_path_or_url=file_path_or_url,
            text_color=text_color,
            background_color=background_color,
            font=font,
            caption=caption,
            preview_type=preview_type,
        )


        return message_id

    async def reply_message(self,to:str,text:str,reply_message_id:str,quoted:Optional[str]=None,message_id:Optional[str]=None,from_me=False):

        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        # Envia mensagem via cliente
        message_id = await self._client.send_text(to, text, message_id=message_id,
                                                    reply_message_id=reply_message_id,
                                                    from_me=from_me,
                                                    quoted=quoted)
        
        return message_id

    async def send_reaction(        
        self,
        to: str,
        reaction: str,
        message_id: Optional[str] = None,
        from_me:Optional[bool] = False):

        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        # Envia mensagem via cliente
        message_id = await self._client.send_reaction(to=to, reaction=reaction,
                                                      message_id=message_id,
                                                      from_me=from_me)
        
        return message_id


    async def remove_reaction(
        self,
        to: str,
        message_id: Optional[str] = None,
        from_me:Optional[bool] = False):


        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        # Envia mensagem via cliente
        message_id = await self._client.send_reaction(to=to, reaction="",
                                                      message_id=message_id,
                                                      from_me=from_me)
        
        return message_id

    
    async def send_text(self, to: str, text: str,message_id:Optional[str]=None, options: Optional[dict] = None) -> str:
        """
        Envia mensagem de texto de forma totalmente assíncrona.
        
        Args:
            to: JID do destinatário (número de telefone ou JID completo)
            text: Texto da mensagem
            options: Opções adicionais (quoted_message, mentions, etc)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        # Envia mensagem via cliente
        message_id = await self._client.send_text(to, text,message_id=message_id, options=options)
        
        return message_id
    

    async def mark_as_read(self, message_id: str,from_jid: str, participant: str = None) -> None:
        """Marca mensagem como lida."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Cliente não conectado")
        await self._client.mark_as_read(message_id, from_jid, participant)
    
    # ========== Mídia ==========
    
    async def send_image(
        self,
        to: str,
        file_path_or_url: str,
        caption: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Envia imagem de forma totalmente assíncrona.
        
        Args:
            to: JID do destinatário (número de telefone ou JID completo)
            file_path_or_url: Caminho do arquivo de imagem ou URL
            caption: Legenda da imagem (opcional)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        message_id = await self._client.send_image(
            to=to,
            file_path_or_url=file_path_or_url,
            caption=caption,
            progress_callback=progress_callback
        )
        
        return message_id
    

    async def get_status_account(self) -> bool:
        """Obtém status da conta."""
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        return await self._client.get_status_account()


    async def send_audio(
        self,
        to: str,
        file_path_or_url: str,
        ptt: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Envia áudio de forma totalmente assíncrona.
        
        Args:
            to: JID do destinatário (número de telefone ou JID completo)
            file_path_or_url: Caminho do arquivo de áudio ou URL
            ptt: Se True, envia como push-to-talk (voice message)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        message_id = await self._client.send_audio(
            to=to,
            file_path_or_url=file_path_or_url,
            ptt=ptt,
            progress_callback=progress_callback
        )
        
        return message_id
    
    async def send_document(
        self,
        to: str,
        file_path_or_url: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Envia documento de forma totalmente assíncrona.
        
        Args:
            to: JID do destinatário (número de telefone ou JID completo)
            file_path_or_url: Caminho do arquivo do documento ou URL
            filename: Nome do arquivo (opcional, usa basename se None)
            caption: Legenda do documento (opcional)
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        message_id = await self._client.send_document(
            to=to,
            file_path_or_url=file_path_or_url,
            filename=filename,
            caption=caption,
            progress_callback=progress_callback
        )
        
        return message_id
    
    async def send_sticker(
        self,
        to: str,
        file_path_or_url: str,
        is_animated: bool = False,
        is_avatar: bool = False,
        is_ai_sticker: bool = False,
        is_lottie: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Envia sticker de forma totalmente assíncrona.
        
        Args:
            to: JID do destinatário (número de telefone ou JID completo)
            file_path_or_url: Caminho do arquivo de sticker ou URL
            is_animated: Se é sticker animado
            is_avatar: Se é avatar sticker
            is_ai_sticker: Se é AI sticker
            is_lottie: Se é Lottie sticker
            progress_callback: Callback para progresso de upload (opcional)
        
        Returns:
            ID da mensagem enviada
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("Not connected")
        
        message_id = await self._client.send_sticker(
            to=to,
            file_path_or_url=file_path_or_url,
            is_animated=is_animated,
            is_avatar=is_avatar,
            is_ai_sticker=is_ai_sticker,
            is_lottie=is_lottie,
            progress_callback=progress_callback
        )
        
        return message_id
    
    # ========== Grupos ==========
    
    async def create_group(self, subject: str, participants: list) -> str:
        """Cria um novo grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.create_group(subject, participants)
    
    async def get_group_info(self, group_jid: str) -> dict:
        """Obtém informações do grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.get_group_info(group_jid)
    
    async def list_groups(self, include_participants: bool = True) -> list:
        """Lista todos os grupos."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.list_groups(include_participants)
    
    async def add_participants(self, group_jid: str, participants: list) -> dict:
        """Adiciona participantes ao grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.add_participants(group_jid, participants)
    
    async def remove_participants(self, group_jid: str, participants: list) -> dict:
        """Remove participantes do grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.remove_participants(group_jid, participants)
    
    async def promote_participants(self, group_jid: str, participants: list) -> bool:
        """Promove participantes a admin."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.promote_participants(group_jid, participants)
    
    async def demote_participants(self, group_jid: str, participants: list) -> bool:
        """Rebaixa participantes de admin."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.demote_participants(group_jid, participants)
    
    async def leave_group(self, group_jid: str) -> bool:
        """Sai do grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.leave_group(group_jid)
    
    async def set_group_subject(self, group_jid: str, subject: str) -> bool:
        """Define assunto do grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.set_subject(group_jid, subject)
    
    async def set_group_description(self, group_jid: str, description: str) -> bool:
        """Define descrição do grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.set_description(group_jid, description)
    
    async def get_group_invite_code(self, group_jid: str) -> str:
        """Obtém código de convite do grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.get_invite_code(group_jid)
    
    async def join_group_with_code(self, code: str) -> str:
        """Entra em grupo com código de convite."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.join_with_code(code)
    
    async def join_group_with_link(self, invite_link: str) -> str:
        """Entra em grupo com link de convite."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.join_group_with_link(invite_link)
    
    async def approve_group_participants(self, group_jid: str, participants: list, action: str = "approve") -> bool:
        """Aprova ou rejeita participantes pendentes."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.approve_participants(group_jid, participants, action)
    
    async def set_group_settings(self, group_jid: str, setting: str, value: str = None) -> bool:
        """Define configurações do grupo."""
        if not self._client or not self._client.group_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.group_handler.set_settings(group_jid, setting, value)
    
    # ========== Contatos ==========
    


  
    async def filter_exists(self, numbers: list, mode: str = "full", context: str = "interactive") -> dict:
        """Sincroniza contatos."""
        if not self._client or not self._client.contact_handler:
            raise ConnectionError("Cliente não conectado")

        result = await self._client.contact_handler.sync_contacts(numbers, mode, context)
        return result.to_dict()

    async def sync_contacts(self, numbers: list, mode: str = "full", context: str = "interactive") -> dict:
        """Sincroniza contatos."""
        if not self._client or not self._client.contact_handler:
            raise ConnectionError("Cliente não conectado")

        new_sync = []

        for number in numbers:
            is_new_contact =  await self._client.axolotl_manager._store.isNewContact(number)
            if is_new_contact:
                new_sync.append(number)

        if len(new_sync) > 0:
            result = await self._client.contact_handler.sync_contacts(new_sync, mode, context)
            for valid_number in result.in_numbers:

                if await self._client.axolotl_manager._store.isNewContact(valid_number):
                    await self._client.axolotl_manager._store.addContact(valid_number,result.lids[valid_number])
                else:
                    await self._client.axolotl_manager._store.updateContact(valid_number,result.lids[valid_number])


            return result.to_dict()

        return {}

    async def integrity_check(self, phones: list) -> dict:
        """
        Verifica integridade de números de telefone.
        
        Args:
            phones: Lista de números de telefone para verificar (ex: ["5511999999999", "5511888888888"])
        
        Returns:
            Dict com resultados da verificação de integridade
        
        Example:
            client.integrity_check(["5511999999999", "5511888888888"])
        """
        if not self._client or not self._client.integrity_handler:
            raise ConnectionError("Cliente não conectado")
        
        result = await self._client.integrity_handler.integrity_check(phones)
        return result


    async def sync_devices(self, jids: list, mode: str = "full", context: str = "interactive") -> list:
        """Sincroniza dispositivos de contatos."""
        if not self._client or not self._client.contact_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.contact_handler.sync_devices(jids, mode, context)
    
    # ========== Typing Indicators ==========


    async def start_recording(self, to: str) -> None:
        """
        Envia indicador de "digitando" para um contato.
        
        Args:
            to: JID do destinatário
        """
        if not self._client:
            raise ConnectionError("Cliente não conectado")
        
        from ..protocol.entities import ChatstateProtocolEntity
        
        await self._client.start_typing(to, media_type = ChatstateProtocolEntity.CHAT_MEDIA_TYPE_AUDIO)


    async def stop_recording(self, to: str) -> None:
        """
        Envia indicador de "digitando" para um contato.
        
        Args:
            to: JID do destinatário
        """
        if not self._client:
            raise ConnectionError("Cliente não conectado")

            
        from ..protocol.entities import ChatstateProtocolEntity
        await self._client.stop_typing(to, media_type = ChatstateProtocolEntity.CHAT_MEDIA_TYPE_AUDIO)


    async def start_typing(self, to: str) -> None:
        """
        Envia indicador de "digitando" para um contato.
        
        Args:
            to: JID do destinatário
        """
        if not self._client:
            raise ConnectionError("Cliente não conectado")
        await self._client.start_typing(to)
    
    async def stop_typing(self, to: str) -> None:
        """
        Para o indicador de "digitando" para um contato.
        
        Args:
            to: JID do destinatário
        """
        if not self._client:
            raise ConnectionError("Cliente não conectado")
        await self._client.stop_typing(to)
    
    async def get_contact_info(self, jid: str) -> dict:
        """Obtém informações de um contato."""
        if not self._client or not self._client.contact_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.contact_handler.get_contact_info(jid)
    
    # ========== Presença ==========
    
    async def set_presence(self, presence_type: str = "available", to: str = None) -> bool:
        """Define presença."""
        if not self._client or not self._client.presence_handler_public:
            raise ConnectionError("Cliente não conectado")
        return await self._client.presence_handler_public.set_presence(presence_type, to)
    
    async def set_status(self, status: str) -> bool:
        """Define status."""
        if not self._client or not self._client.presence_handler_public:
            raise ConnectionError("Cliente não conectado")
        return await self._client.presence_handler_public.set_status(status)
    

    # ========== Proxy ==========
    
    async def set_proxy(self, proxy_string:str,proxy_type:str="http") -> bool:
        """Define proxy."""

        self.proxy = await WhatsAppClient.new_proxy(proxy_string=proxy_string,proxy_type=proxy_type)
        if not self.proxy:
            self.proxy = None
            return False

        if self._client:
            return await self._client.set_proxy(proxy_string=proxy_string,proxy_type=proxy_type)

        return True
    
    async def get_proxy(self) -> Optional[ProxyConfig]:
        """Obtém proxy."""
        if self._client:
            return await self._client.get_proxy()
        return self.proxy
    
    async def remove_proxy(self) -> bool:
        """Remove proxy."""
        return await self._client.remove_proxy()
    
    async def get_proxy_status(self) -> bool:
        """Obtém status do proxy."""
        return await self._client.get_proxy_status()
    
    # ========== Perfil ==========

    async def get_my_avatar(self) -> ProfileResponse:
        """Obtém avatar da conta. Retorna ProfileResponse (data com has_avatar/url ou error_code)."""
        if not self._client or not self._client.profile_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.profile_handler.get_avatar(self.account_id)

    async def get_avatar(self, jid: str) -> ProfileResponse:
        """Obtém URL e metadados do avatar de um contato. Retorna ProfileResponse."""
        if not self._client or not self._client.profile_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.profile_handler.get_avatar(jid)

    async def set_avatar(self, avatar_source: str) -> ProfileResponse:
        """
        Define o avatar da conta a partir de URL ou arquivo local.
        Redimensiona para 640x640 (foto) e 96x96 (preview) em JPEG.
        Retorna ProfileResponse.
        """
        if not self._client or not self._client.profile_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.profile_handler.set_avatar(avatar_source)

    async def get_status(self, jid: str) -> ProfileResponse:
        """Obtém status de um contato. Retorna ProfileResponse (data com texto ou None)."""
        if not self._client or not self._client.profile_handler:
            raise ConnectionError("Cliente não conectado")
        return await self._client.profile_handler.get_status(jid)
    
  
    
    async def disconnect(self) -> None:
        """Desconecta de forma assíncrona e finaliza todos os recursos (incl. emitter)."""
        if self._client:
            await self._client.disconnect()
        try:
            self._events.shutdown()
        except Exception:
            pass

    
    def on_message(self, handler: Callable) -> None:
        """Registra handler de mensagem"""
        self._events.on("message", handler)
    
    def on_connected(self, handler: Callable) -> None:
        """Registra handler de conexão"""
        self._events.on("connected", handler)
    
    def on_disconnected(self, handler: Callable) -> None:
        """Registra handler de desconexão"""
        self._events.on("disconnected", handler)












