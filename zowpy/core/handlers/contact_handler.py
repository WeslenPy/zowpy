"""
Contact Handler - Gerencia operações de contatos.

Handler público para todas as operações de contatos do WhatsApp.
"""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...utils.jid import to_whatsapp_jid
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
            numbers: Lista de números de telefone (com ou sem +, ou JIDs)
            mode: Modo de sync (full ou delta)
            context: Contexto (registration ou interactive)
        
        Returns:
            Dict com informações dos contatos sincronizados
        
        Raises:
            Exception: Se sync falhar
        """
        # CORREÇÃO: Normaliza números/JIDs antes de usar
        normalized_numbers = []
        for number in numbers:
            try:
                # Se for JID, extrai apenas o número
                if "@" in number:
                    # Extrai apenas a parte antes do @
                    num = number.split("@")[0]
                    # Remove device_id se existir
                    if ":" in num:
                        num = num.split(":")[0]
                    normalized_numbers.append(num)
                else:
                    # Já é um número, remove device_id se existir
                    if ":" in number:
                        normalized_numbers.append(number.split(":")[0])
                    else:
                        normalized_numbers.append(number)
            except Exception as e:
                logger.warning(f"Erro ao normalizar número '{number}': {e}, usando como está")
                normalized_numbers.append(number)
        
        logger.info(f"Sincronizando contatos: {len(normalized_numbers)} números, mode={mode}")
        logger.debug(f"Números normalizados: {normalized_numbers}")
        
        iq_node = ContactBuilder.build_sync_contacts(
            numbers=normalized_numbers,
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
            jids: Lista de JIDs dos contatos (pode ser número, JID parcial ou completo)
            mode: Modo de sync (full ou delta)
            context: Contexto (registration ou interactive)
        
        Returns:
            Lista de JIDs de dispositivos encontrados
        
        Raises:
            Exception: Se sync falhar
        """
        # CORREÇÃO: Normaliza JIDs antes de usar
        # Aceita números simples, JIDs parciais ou completos
        normalized_jids = []
        for jid in jids:
            try:
                # Remove @ e sufixo se existir, mantém apenas o número
                # Para sync_devices, precisamos apenas do número (sem @s.whatsapp.net)
                if "@" in jid:
                    # Extrai apenas a parte antes do @
                    number = jid.split("@")[0]
                    # Remove device_id se existir (ex: "559885700260:0" -> "559885700260")
                    if ":" in number:
                        number = number.split(":")[0]
                    normalized_jids.append(number)
                else:
                    # Já é um número, remove device_id se existir
                    if ":" in jid:
                        normalized_jids.append(jid.split(":")[0])
                    else:
                        normalized_jids.append(jid)
            except Exception as e:
                logger.warning(f"Erro ao normalizar JID '{jid}': {e}, usando como está")
                normalized_jids.append(jid)
        
        logger.info(f"Sincronizando dispositivos: {len(normalized_jids)} contatos, mode={mode}")
        logger.debug(f"JIDs normalizados: {normalized_jids}")
        
        iq_node = ContactBuilder.build_sync_devices(
            jids=normalized_jids,
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
            jid: JID do contato (pode ser número, JID parcial ou completo)
        
        Returns:
            Dict com informações do contato
        
        Raises:
            Exception: Se obtenção falhar
        """
        # CORREÇÃO: Normaliza JID antes de usar
        try:
            # Extrai número do JID, removendo @ e device_id se existir
            if "@" in jid:
                number = jid.split("@")[0]
            else:
                number = jid
            
            # Remove device_id se existir (ex: "559885700260:0" -> "559885700260")
            if ":" in number:
                number = number.split(":")[0]
        except Exception as e:
            logger.warning(f"Erro ao normalizar JID '{jid}': {e}, usando como está")
            number = jid
        
        # Sincroniza contato (sync_contacts já normaliza internamente, mas fazemos aqui também)
        result = await self.sync_contacts([number])
        
        # Retorna informações (estrutura pode variar)
        return {
            "jid": jid,
            "number": number,
            "sync_result": result
        }

