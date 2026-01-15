"""
Profile Handler - Gerencia operações de perfil.

Handler público para foto de perfil e status do WhatsApp.
"""

import asyncio
from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from ..builders.iq_builder import IQBuilder
from ..processors.iq_response import IQResponseProcessor


class ProfileHandler:
    """
    Gerencia operações de perfil.
    
    Métodos públicos para obter/definir foto de perfil e status.
    """
    
    # XMLNS para operações de perfil
    XMLNS_PROFILE = "w:profile:picture"
    XMLNS_STATUS = "status"
    
    def __init__(
        self,
        send_iq_fn: callable,
        iq_response_processor: IQResponseProcessor
    ):
        """
        Inicializa handler.
        
        Args:
            send_iq_fn: Função async para enviar IQ (recebe ProtocolNode)
            iq_response_processor: Processor para gerenciar respostas de IQ
        """
        self._send_iq = send_iq_fn
        self._iq_processor = iq_response_processor
    
    async def get_profile_picture(self, jid: str) -> Optional[bytes]:
        """
        Obtém foto de perfil.
        
        Args:
            jid: JID do contato
        
        Returns:
            Bytes da foto ou None se não houver
        
        Raises:
            Exception: Se obtenção falhar
        """
        logger.info(f"Obtendo foto de perfil: {jid}")
        
        iq_node = IQBuilder.build_base_iq(
            xmlns=ProfileHandler.XMLNS_PROFILE,
            iq_type="get",
            to=jid
        )
        
        # Adiciona node <picture>
        picture_node = ProtocolNode(
            tag="picture",
            attributes={},
            children=[]
        )
        iq_node.children.append(picture_node)
        
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de foto de perfil"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao obter foto: tipo={node.get_attribute('type')}"))
                    return
                
                # Extrai foto do node <picture>
                picture_node = node.get_child("picture")
                if picture_node:
                    picture_data = picture_node.data
                    if picture_data:
                        logger.info("Foto de perfil obtida com sucesso")
                        future.set_result(picture_data)
                        return
                
                # Sem foto
                logger.info("Contato não possui foto de perfil")
                future.set_result(None)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando foto de perfil")
    
    async def set_profile_picture(self, picture_data: bytes) -> bool:
        """
        Define foto de perfil.
        
        Args:
            picture_data: Bytes da foto
        
        Returns:
            True se sucesso
        
        Raises:
            Exception: Se definição falhar
        """
        logger.info(f"Definindo foto de perfil: {len(picture_data)} bytes")
        
        iq_node = IQBuilder.build_base_iq(
            xmlns=ProfileHandler.XMLNS_PROFILE,
            iq_type="set"
        )
        
        # Adiciona node <picture> com dados
        picture_node = ProtocolNode(
            tag="picture",
            attributes={},
            data=picture_data
        )
        iq_node.children.append(picture_node)
        
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de definição de foto"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao definir foto: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info("Foto de perfil definida com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando definição de foto de perfil")
    
    async def get_status(self, jid: str) -> Optional[str]:
        """
        Obtém status de um contato.
        
        Args:
            jid: JID do contato
        
        Returns:
            Texto do status ou None se não houver
        
        Raises:
            Exception: Se obtenção falhar
        """
        logger.info(f"Obtendo status: {jid}")
        
        iq_node = IQBuilder.build_base_iq(
            xmlns=ProfileHandler.XMLNS_STATUS,
            iq_type="get",
            to=jid
        )
        
        # Adiciona node <status>
        status_node = ProtocolNode(
            tag="status",
            attributes={},
            children=[]
        )
        iq_node.children.append(status_node)
        
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de status"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao obter status: tipo={node.get_attribute('type')}"))
                    return
                
                # Extrai status do node <status>
                status_node = node.get_child("status")
                if status_node:
                    status_data = status_node.data
                    if status_data:
                        status_text = status_data.decode("utf-8") if isinstance(status_data, bytes) else status_data
                        logger.info(f"Status obtido: {status_text[:50]}")
                        future.set_result(status_text)
                        return
                
                # Sem status
                logger.info("Contato não possui status")
                future.set_result(None)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando status")

