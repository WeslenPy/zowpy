"""
Contact Handler - Gerencia operações de contatos.

Handler público para todas as operações de contatos do WhatsApp.
"""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from ..builders.contact_builder import ContactBuilder
from ..processors.iq_response import IQResponseProcessor


class ContactHandler:
    """
    Gerencia operações de contatos.
    
    Métodos públicos para sincronizar contatos e dispositivos.
    """
    
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
    
    async def sync_contacts(
        self,
        numbers: List[str],
        mode: str = ContactBuilder.MODE_FULL,
        context: str = ContactBuilder.CONTEXT_INTERACTIVE
    ) -> Dict[str, Any]:
        """
        Sincroniza contatos.
        
        Args:
            numbers: Lista de números de telefone (com ou sem +)
            mode: Modo de sync (full ou delta)
            context: Contexto (registration ou interactive)
        
        Returns:
            Dict com informações dos contatos sincronizados
        
        Raises:
            Exception: Se sync falhar
        """
        logger.info(f"Sincronizando contatos: {len(numbers)} números, mode={mode}")
        
        iq_node = ContactBuilder.build_sync_contacts(
            numbers=numbers,
            mode=mode,
            context=context
        )
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de sync de contatos"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao sincronizar contatos: tipo={node.get_attribute('type')}"))
                    return
                
                # Extrai informações do node <usync>
                usync_node = node.get_child("usync")
                if not usync_node:
                    future.set_exception(Exception("Resposta sem node <usync>"))
                    return
                
                result = {
                    "version": usync_node.get_attribute("version") or "",
                    "mode": usync_node.get_attribute("mode") or mode,
                    "in_numbers": [],
                    "out_numbers": [],
                    "wait": usync_node.get_attribute("wait") or None
                }
                
                # Extrai números in e out
                # A estrutura pode variar, mas geralmente está em nodes filhos
                # Por enquanto, retorna estrutura básica
                logger.info(f"Contatos sincronizados: version={result['version']}, mode={result['mode']}")
                future.set_result(result)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando sincronização de contatos")
    
    async def sync_devices(
        self,
        jids: List[str],
        mode: str = ContactBuilder.MODE_FULL,
        context: str = ContactBuilder.CONTEXT_INTERACTIVE
    ) -> List[str]:
        """
        Sincroniza dispositivos de contatos.
        
        Args:
            jids: Lista de JIDs dos contatos
            mode: Modo de sync (full ou delta)
            context: Contexto (registration ou interactive)
        
        Returns:
            Lista de JIDs de dispositivos encontrados
        
        Raises:
            Exception: Se sync falhar
        """
        logger.info(f"Sincronizando dispositivos: {len(jids)} contatos, mode={mode}")
        
        iq_node = ContactBuilder.build_sync_devices(
            jids=jids,
            mode=mode,
            context=context
        )
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de sync de dispositivos"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao sincronizar dispositivos: tipo={node.get_attribute('type')}"))
                    return
                
                # Extrai dispositivos do node <usync>
                usync_node = node.get_child("usync")
                if not usync_node:
                    future.set_exception(Exception("Resposta sem node <usync>"))
                    return
                
                devices = []
                
                # Procura por nodes de dispositivos
                # A estrutura pode variar, mas geralmente está em nodes filhos
                list_node = usync_node.get_child("list")
                if list_node:
                    for user_node in list_node.children:
                        if user_node.tag == "user":
                            # Extrai JID do dispositivo
                            # A estrutura pode variar
                            jid = user_node.get_attribute("jid")
                            if jid:
                                devices.append(jid)
                
                logger.info(f"Dispositivos sincronizados: {len(devices)} dispositivos")
                future.set_result(devices)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando sincronização de dispositivos")
    
    async def get_contact_info(self, jid: str) -> Dict[str, Any]:
        """
        Obtém informações de um contato.
        
        Usa sync_contacts internamente.
        
        Args:
            jid: JID do contato
        
        Returns:
            Dict com informações do contato
        
        Raises:
            Exception: Se obtenção falhar
        """
        # Extrai número do JID
        number = jid.split("@")[0] if "@" in jid else jid
        
        # Sincroniza contato
        result = await self.sync_contacts([number])
        
        # Retorna informações (estrutura pode variar)
        return {
            "jid": jid,
            "number": number,
            "sync_result": result
        }

