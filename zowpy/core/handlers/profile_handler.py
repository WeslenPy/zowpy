"""
Profile Handler - Gerencia operações de perfil.

Handler público para foto de perfil, status, pushname e business name do WhatsApp.
"""

import asyncio
import os
import time
from typing import Optional, Dict, Any, Tuple, Callable, Awaitable
from loguru import logger

from zowpy.core.builders.contact_builder import ContactBuilder
from zowpy.protocol.entities.iq_get_business_profile import GetBusinessProfileIqProtocolEntity
from zowpy.utils.jid import to_whatsapp_jid
from zowpy.utils.tools import Jid

from ...protocol.structs import ProtocolNode
from ...protocol.iq import AppSyncStateIqProtocolEntity
from ...protocol.historysync.attributes.attributes_sync_action_data import SyncActionDataAttribute
from ...protocol.historysync.attributes.attributes_sync_action_pushname_setting import SyncActionPushnameSettingAttribute
from ...protocol.historysync.attributes.attributes_sync_action_value import SyncActionValueAttribute
from ...protocol.historysync.hash_state import HashState
from ...protocol.historysync.mutation_keys import MutationKeys
from ...protocol.historysync.patch_builder import PatchBuilder
from ...protocol.entities import SetBusinessNameIqProtocolEntity, UpdateBusinessProfileIqProtocolEntity
from ...utils.media_tools import normalize_file_path_or_url, ImageTools
from ..builders.iq_builder import IQBuilder
from ..processors.iq_response import IQResponseProcessor
from .profile_response import ProfileResponse


class ProfileHandler:
    """
    Gerencia operações de perfil.

    Métodos públicos para obter/definir foto de perfil, status, pushname e business name.
    """

    # XMLNS para operações de perfil
    XMLNS_PROFILE = "w:profile:picture"
    XMLNS_STATUS = "status"

    def __init__(
        self,
        send_iq_fn: callable,
        iq_response_processor: IQResponseProcessor,
        *,
        get_app_state_key: Optional[Callable[[], Awaitable[Any]]] = None,
        config: Optional[Any] = None,
        profile: Optional[Any] = None,
        get_private_signing_key: Optional[Callable[[], Any]] = None,
    ):
        """
        Inicializa handler.

        Args:
            send_iq_fn: Função async para enviar IQ (recebe ProtocolNode)
            iq_response_processor: Processor para gerenciar respostas de IQ
            get_app_state_key: (opcional) Async callable para obter chave AppState (set_profile_name)
            config: (opcional) Config com is_business, pushname, business_name
            profile: (opcional) AsyncProfile com write_config
            get_private_signing_key: (opcional) Callable que retorna chave privada (set_business_name)
        """
        self._send_iq = send_iq_fn
        self._iq_processor = iq_response_processor
        self._get_app_state_key = get_app_state_key
        self._config = config
        self._profile = profile
        self._get_private_signing_key = get_private_signing_key
    

    
    async def set_profile_picture(
        self,
        picture_data: bytes,
        preview_data: Optional[bytes] = None
    ) -> ProfileResponse:
        """
        Define foto de perfil.

        Quando preview_data é informado, envia IQ no formato completo
        (picture 640x640 + preview 96x96) para s.whatsapp.net.

        Args:
            picture_data: Bytes da foto (imagem principal, ex.: JPEG 640x640)
            preview_data: Bytes da miniatura (ex.: JPEG 96x96). Opcional.

        Returns:
            ProfileResponse com success, message ou error_message/error_code.
        """
        logger.info(f"Definindo foto de perfil: {len(picture_data)} bytes")
        to_jid = "s.whatsapp.net" if preview_data is not None else None
        iq_node = IQBuilder.build_base_iq(
            xmlns=ProfileHandler.XMLNS_PROFILE,
            iq_type="set",
            to=to_jid
        )
        if preview_data is not None:
            picture_id = str(int(time.time()))
            picture_node = ProtocolNode(
                tag="picture",
                attributes={"type": "image", "id": picture_id},
                data=picture_data
            )
            preview_node = ProtocolNode(
                tag="picture",
                attributes={"type": "preview"},
                data=preview_data
            )
            iq_node.children.append(picture_node)
            iq_node.children.append(preview_node)
        else:
            picture_node = ProtocolNode(
                tag="picture",
                attributes={},
                data=picture_data
            )
            iq_node.children.append(picture_node)
        
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()
        
        async def on_response(node: ProtocolNode):
            try:
                if node.get_attribute("type") != "result":
                    code = node.get_attribute("code") or node.get_attribute("type") or "unknown"
                    reason = node.get_attribute("reason")
                    if not future.done():
                        future.set_result(ProfileResponse.fail(
                            error_message="Erro ao definir foto de perfil",
                            error_code=code,
                            reason=reason,
                        ))
                    return
                logger.info("Foto de perfil definida com sucesso")
                if not future.done():
                    future.set_result(ProfileResponse.ok(message="Foto de perfil definida com sucesso"))
            except Exception as e:
                if not future.done():
                    future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message="Timeout aguardando definição de foto de perfil",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )

    async def set_avatar(self, avatar_source: str) -> ProfileResponse:
        """
        Define o avatar da conta a partir de URL ou arquivo local.

        Usa media_tools para normalizar URL/arquivo e redimensionar para
        640x640 (foto) e 96x96 (preview) em JPEG.

        Args:
            avatar_source: URL (http(s)://) ou caminho absoluto/relativo do arquivo

        Returns:
            ProfileResponse com success, message ou error_message/error_code.
        """
        filepath: Optional[str] = None
        is_temporary = False
        try:
            filepath, is_temporary = await normalize_file_path_or_url(
                avatar_source, default_extension=".jpg", prefix="avatar"
            )
        except Exception as e:
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="invalid_source",
                errors=[str(e)],
            )
        try:
            def _resize() -> Tuple[bytes, bytes]:
                picture_data = ImageTools.resize_to_jpeg(filepath, 640, 640)
                preview_data = ImageTools.resize_to_jpeg(filepath, 96, 96)
                return picture_data, preview_data

            loop = asyncio.get_event_loop()
            picture_data, preview_data = await loop.run_in_executor(None, _resize)
            return await self.set_profile_picture(picture_data, preview_data)
        except Exception as e:
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="resize_or_upload",
                errors=[str(e)],
            )
        finally:
            if filepath and is_temporary and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass

    async def get_avatar(self, jid: str) -> ProfileResponse:
        """
        Obtém URL e metadados do avatar (foto de perfil) de um contato.

        Envia IQ get com query=url para s.whatsapp.net; a resposta traz
        id, type e url da imagem. Retorna ProfileResponse com data quando
        há avatar; success=False e error_code quando não há ou erro.

        Args:
            jid: JID do contato (número ou JID completo).

        Returns:
            ProfileResponse: data com has_avatar/id/type/url em sucesso; error_code em falha.
        """
        try:
            target_jid = to_whatsapp_jid(jid) if jid else None
        except Exception as e:
            return ProfileResponse.fail(
                error_message="JID inválido",
                error_code="invalid_jid",
                reason=str(e),
            )
        if not target_jid:
            return ProfileResponse.fail(
                error_message="JID vazio ou inválido",
                error_code="invalid_jid",
            )

        logger.info(f"Obtendo avatar (URL) para: {target_jid}")
        iq_node = IQBuilder.build_base_iq(
            xmlns=ProfileHandler.XMLNS_PROFILE,
            iq_type="get",
            to="s.whatsapp.net"
        )
        iq_node.attributes["target"] = target_jid
        picture_node = ProtocolNode(
            tag="picture",
            attributes={"type": "image", "query": "url"},
            children=[]
        )
        iq_node.children.append(picture_node)
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_response(node: ProtocolNode) -> None:
            try:
                resp_type = node.get_attribute("type")
                if resp_type == "error":
                    code = node.get_attribute("code") or node.get_attribute("reason") or "unknown"
                    reason = node.get_attribute("reason")
                    if not future.done():
                        future.set_result(ProfileResponse.fail(
                            data={"has_avatar": False},
                            error_message="Erro ao obter avatar",
                            error_code=code,
                            reason=reason,
                        ))
                    return
                if resp_type != "result":
                    if not future.done():
                        future.set_result(ProfileResponse.fail(
                            data={"has_avatar": False},
                            error_code=resp_type or "unknown",
                        ))
                    return
                picture_node_resp = node.get_child("picture")
                if not picture_node_resp:
                    if not future.done():
                        future.set_result(ProfileResponse.ok(
                            data={"has_avatar": False},
                            message="Sem foto de perfil",
                        ))
                    return
                url = picture_node_resp.get_attribute("url")
                if not url:
                    if not future.done():
                        future.set_result(ProfileResponse.ok(
                            data={"has_avatar": False},
                            message="Sem URL de avatar",
                        ))
                    return
                result = {
                    "has_avatar": True,
                    "id": picture_node_resp.get_attribute("id") or "",
                    "type": picture_node_resp.get_attribute("type") or "image",
                    "url": url,
                }
                if not future.done():
                    future.set_result(ProfileResponse.ok(data=result, message="Avatar obtido"))
            except Exception as e:
                if not future.done():
                    future.set_exception(e)

        timeout = 30.0
        self._iq_processor.register_callback(iq_id, on_response, timeout=timeout)
        await self._send_iq(iq_node)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                data={"has_avatar": False},
                error_message="Timeout ao obter avatar",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                data={"has_avatar": False},
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )

    async def get_account_info(self) -> ProfileResponse:
        """
        Obtém informações da conta (creation, last_reg).

        Envia IQ get para urn:xmpp:whatsapp:account; a resposta traz
        os atributos creation e last_reg no node <account>.

        Returns:
            ProfileResponse: data com creation e last_reg em sucesso; error_code em falha.
        """
        XMLNS_ACCOUNT = "urn:xmpp:whatsapp:account"
        logger.info("Obtendo informações da conta (account info)")
        iq_node = IQBuilder.build_base_iq(
            xmlns=XMLNS_ACCOUNT,
            iq_type="get",
            to="s.whatsapp.net"
        )
        iq_node.children.append(ProtocolNode(tag="account", attributes={}, children=[]))
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_response(node: ProtocolNode) -> None:
            try:
                resp_type = node.get_attribute("type")
                if resp_type == "error":
                    code = node.get_attribute("code") or node.get_attribute("reason") or "unknown"
                    reason = node.get_attribute("reason")
                    if not future.done():
                        future.set_result(ProfileResponse.fail(
                            error_message="Erro ao obter informações da conta",
                            error_code=code,
                            reason=reason,
                        ))
                    return
                if resp_type != "result":
                    if not future.done():
                        future.set_result(ProfileResponse.fail(
                            error_code=resp_type or "unknown",
                        ))
                    return
                account_node = node.get_child("account")
                if not account_node:
                    if not future.done():
                        future.set_result(ProfileResponse.fail(error_code="no_account_node"))
                    return
                creation_s = account_node.get_attribute("creation")
                last_reg_s = account_node.get_attribute("last_reg")
                try:
                    creation = int(creation_s) if creation_s is not None else None
                    last_reg = int(last_reg_s) if last_reg_s is not None else None
                except (TypeError, ValueError):
                    if not future.done():
                        future.set_result(ProfileResponse.fail(
                            error_message="Valores creation/last_reg inválidos",
                            error_code="parse_error",
                        ))
                    return
                if not future.done():
                    future.set_result(ProfileResponse.ok(
                        data={"creation": creation, "last_reg": last_reg},
                        message="Informações da conta obtidas",
                    ))
            except Exception as e:
                if not future.done():
                    future.set_exception(e)

        timeout = 30.0
        self._iq_processor.register_callback(iq_id, on_response, timeout=timeout)
        await self._send_iq(iq_node)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message="Timeout aguardando informações da conta",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )

    async def get_status(self, jid: str) -> ProfileResponse:
        """
        Obtém status de um contato.

        Args:
            jid: JID do contato

        Returns:
            ProfileResponse: data com texto do status (ou None se não houver); error_code em falha.
        """
        logger.info(f"Obtendo status: {jid}")
        iq_node = IQBuilder.build_base_iq(
            xmlns=ProfileHandler.XMLNS_STATUS,
            iq_type="get",
            to=jid
        )
        status_node = ProtocolNode(
            tag="status",
            attributes={},
            children=[]
        )
        iq_node.children.append(status_node)
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_response(node: ProtocolNode):
            try:
                if node.get_attribute("type") != "result":
                    code = node.get_attribute("code") or node.get_attribute("type") or "unknown"
                    if not future.done():
                        future.set_result(ProfileResponse.fail(
                            error_message="Erro ao obter status",
                            error_code=code,
                        ))
                    return
                status_node_resp = node.get_child("status")
                if status_node_resp and status_node_resp.data:
                    status_data = status_node_resp.data
                    status_text = status_data.decode("utf-8") if isinstance(status_data, bytes) else status_data
                    logger.info(f"Status obtido: {status_text[:50]}")
                    if not future.done():
                        future.set_result(ProfileResponse.ok(data=status_text, message="Status obtido"))
                    return
                logger.info("Contato não possui status")
                if not future.done():
                    future.set_result(ProfileResponse.ok(data=None, message="Sem status"))
            except Exception as e:
                if not future.done():
                    future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message="Timeout aguardando status",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )

    async def set_profile_name(self, name: str) -> ProfileResponse:
        """
        Define o nome da conta (pushname) usando AppState Sync.
        Alinhado ao setName do zowsuplib (yowbot_layer).
        """
        if not self._config or self._config.is_business:
            return ProfileResponse.fail(
                error_message="Conta é business; não pode alterar pushname",
                error_code="business_account",
            )
        if not self._get_app_state_key or not self._profile:
            return ProfileResponse.fail(
                error_message="ProfileHandler não configurado para set_profile_name",
                error_code="not_configured",
            )
        try:
            key = await self._get_app_state_key()
        except Exception as e:
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="app_state_key",
                errors=[str(e)],
            )
        mutation_keys = MutationKeys.createFromKey(key.key_data.key_data)
        push_name_setting = SyncActionDataAttribute.createFromSyncActionValue(
            SyncActionValueAttribute(
                pushNameSetting=SyncActionPushnameSettingAttribute(name=name)
            )
        )
        state = HashState("critical_block", 0)
        state, syncd_patch = PatchBuilder(state, mutation_keys, key).addMutation(push_name_setting).finish()
        patches = {"critical_block": syncd_patch.encode()}
        entity = AppSyncStateIqProtocolEntity(patches=patches)
        iq_node = entity.toProtocolTreeNode()
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_iq_response(node: ProtocolNode) -> None:
            resp_type = node.get_attribute("type")
            if resp_type == "result":
                logger.info("set_profile_name (AppState Sync) success")
                if self._profile and self._config:
                    self._config.pushname = name
                    await self._profile.write_config(self._config)
                if not future.done():
                    future.set_result(ProfileResponse.ok(message="Nome da conta atualizado"))
            else:
                code = node.get_attribute("code") or node.get_attribute("reason") or "unknown"
                reason = node.get_attribute("reason")
                logger.error(f"set_profile_name (AppState Sync) error: {code}")
                if not future.done():
                    future.set_result(ProfileResponse.fail(
                        error_message="Erro ao atualizar nome da conta",
                        error_code=code,
                        reason=reason,
                    ))

        timeout = 30.0
        try:
            self._iq_processor.register_callback(iq_id, on_iq_response, timeout=timeout)
            await self._send_iq(iq_node)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message="Timeout aguardando resposta do set_profile_name",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )

    async def set_business_name(self, name: str) -> Dict[str, Any]:
        """
        Define o nome de negócio verificado (business / SMB).
        """
        if not self._config or not self._config.is_business:
            raise Exception("Conta não é business")

        if not self._get_private_signing_key or not self._profile:
            raise Exception("ProfileHandler não configurado para set_business_name (get_private_signing_key/profile)")

        private_key = self._get_private_signing_key()
        entity = SetBusinessNameIqProtocolEntity(name=name, private_signing_key=private_key)
        iq_node = entity.to_protocol_node()
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_iq_response(node: ProtocolNode) -> None:
            resp_type = node.get_attribute("type")
            if resp_type == "result":
                logger.info("set_business_name (w:biz) success")
                if self._config:
                    self._config.business_name = name
                    await self._profile.write_config(self._config)
                if not future.done():
                    future.set_result({"success": True})
            else:
                code = node.get_attribute("code") or node.get_attribute("reason") or "unknown"
                err = Exception(f"set_business_name error: {code}")
                logger.error(f"set_business_name (w:biz) error: {code}")
                if not future.done():
                    future.set_result({"success": False, "code": code})

        timeout = 30.0
        try:
            self._iq_processor.register_callback(iq_id, on_iq_response, timeout=timeout)
            await self._send_iq(iq_node)
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando resposta do set_business_name (w:biz)")
        except Exception:
            self._iq_processor.unregister_callback(iq_id)
            raise


    async def set_update_business_profile(self, info_type: str, info_data: str) -> ProfileResponse:
        """Atualiza o perfil business (w:biz)."""
        if not self._config or not self._config.is_business:
            return ProfileResponse.fail(
                error_message="Conta não é business",
                error_code="not_business",
            )
        try:
            entity = UpdateBusinessProfileIqProtocolEntity(info_type=info_type, info_data=info_data)
        except Exception as e:
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="invalid_input",
                errors=[str(e)],
            )
        iq_node = entity.to_protocol_node()
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_iq_response(node: ProtocolNode) -> None:
            resp_type = node.get_attribute("type")
            if resp_type == "result":
                logger.info("set_update_business_profile (w:biz) success")
                if not future.done():
                    future.set_result(ProfileResponse.ok(message="Perfil business atualizado"))
            else:
                code = node.get_attribute("code") or node.get_attribute("reason") or "unknown" 
                reason = node.get_attribute("reason")
                logger.error(f"set_update_business_profile (w:biz) error: {code}")
                if not future.done():
                    future.set_result(ProfileResponse.fail(
                        error_message="Erro ao atualizar perfil business",
                        error_code=code,
                        reason=reason,
                    ))
        timeout = 30.0
        try:
            self._iq_processor.register_callback(iq_id, on_iq_response, timeout=timeout)
            await self._send_iq(iq_node)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message="Timeout aguardando resposta do set_update_business_profile",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )


    async def set_description_business(self, description: str) -> ProfileResponse:
        """Define a descrição do perfil business (w:biz)."""
        return await self.set_update_business_profile(info_type="description", info_data=description)

    async def set_email_business(self, email: str) -> ProfileResponse:
        """Define o email do perfil business (w:biz)."""
        return await self.set_update_business_profile(info_type="email", info_data=email)

    async def set_website_business(self, website: str) -> ProfileResponse:
        """Define o website do perfil business (w:biz)."""
        return await self.set_update_business_profile(info_type="website", info_data=website)

    async def set_address_business(self, address: str) -> ProfileResponse:
        """Define o endereço do perfil business (w:biz)."""
        return await self.set_update_business_profile(info_type="address", info_data=address)


    async def get_business_profile(self, jid: str) -> ProfileResponse:
        """Obtém o perfil business (w:biz)."""

        jid = to_whatsapp_jid(jid)
        if not jid:
            return ProfileResponse.fail(
                error_message="JID inválido",
                error_code="invalid_jid",
            )
        
        entity = GetBusinessProfileIqProtocolEntity(jid=jid)

        iq_node = entity.to_protocol_node()
        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_iq_response(node: ProtocolNode) -> None:
            resp_type = node.get_attribute("type")
            if resp_type == "result":
                logger.info("get_business_profile (w:biz) success")
                logger.info(f"Perfil business obtido: {node}")
                if not future.done():
                    future.set_result(ProfileResponse.ok(message="Perfil business obtido", data=node))
            else:
                code = node.get_attribute("code") or node.get_attribute("reason") or "unknown"
                reason = node.get_attribute("reason")
                logger.error(f"get_business_profile (w:biz) error: {code}")
                if not future.done():
                    future.set_result(ProfileResponse.fail(
                        error_message="Erro ao obter perfil business",
                        error_code=code,
                        reason=reason,
                    ))

        timeout = 30.0
        try:
            self._iq_processor.register_callback(iq_id, on_iq_response, timeout=timeout)
            await self._send_iq(iq_node)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message="Timeout aguardando resposta do get_business_profile",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )



    async def get_user_info(self, jid: str) -> ProfileResponse:
        """Obtém informações do usuário (usync)."""

        query = [
            ProtocolNode(tag="status", attributes={}),
            ProtocolNode(tag="business", attributes={}, children=[ProtocolNode(tag="verified_name", attributes={}, children=[])]),
            ProtocolNode(tag="picture", attributes={}),
            ProtocolNode(tag="devices", attributes={"version": "2"}, children=[]),
            ProtocolNode(tag="lid", attributes={}),
        ]

        iq_node = ContactBuilder.build_sync_contacts(
                numbers=[jid],
                mode=ContactBuilder.MODE_FULL, 
                context=ContactBuilder.CONTEXT_BACKGROUND, 
                query=query)

        iq_id = iq_node.get_attribute("id")
        future = asyncio.get_running_loop().create_future()

        async def on_iq_response(node: ProtocolNode) -> None:
            resp_type = node.get_attribute("type")
            if resp_type == "result":
                logger.info("get_user_info (usync) success")
                logger.info(f"Informações do usuário obtidas: {node}")
                if not future.done():
                    future.set_result(ProfileResponse.ok(message="Informações do usuário obtidas", data=node))
            else:
                code = node.get_attribute("code") or node.get_attribute("reason") or "unknown"
                reason = node.get_attribute("reason")
                logger.error(f"get_user_info (usync) error: {code}")
                if not future.done():
                    future.set_result(ProfileResponse.fail(
                        error_message="Erro ao obter informações do usuário",
                        error_code=code,
                        reason=reason,
                    ))


        timeout = 30.0
        try:
            self._iq_processor.register_callback(iq_id, on_iq_response, timeout=timeout)
            await self._send_iq(iq_node)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message="Timeout aguardando resposta do get_user_info",
                error_code="timeout",
            )
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            return ProfileResponse.fail(
                error_message=str(e),
                error_code="exception",
                errors=[str(e)],
            )