"""
Integrity Handler - Gerencia operações de checagem de integridade.

Handler público para checagem de integridade de contatos via BizIntegrityQuery.
"""

import asyncio
from typing import List, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...utils.jid import normalize, to_whatsapp_jid
from ...protocol.entities.iq_wmex import (
    WmexQueryIqProtocolEntity,
    WmexResultIqProtocolEntity
)
from ..processors.iq_response import IQResponseProcessor


class IntegrityHandler:
    """
    Gerencia operações de checagem de integridade.
    
    Métodos públicos para verificar integridade de contatos.
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
    
    async def integrity_check(self, phones: List[str]) -> Dict[str, Any]:
        """
        Verifica integridade de números de telefone.
        
        Args:
            phones: Lista de números de telefone para verificar
        
        Returns:
            Dict com resultado da verificação
        
        Raises:
            Exception: Se verificação falhar
        """
        # Normaliza e converte para JIDs completos
        jids = []
        for phone in phones:
            try:
                # Normaliza número (remove caracteres não numéricos)
                normalized = normalize(phone)
                if not normalized:
                    logger.warning(f"Número inválido: {phone}")
                    continue
                
                # Converte para JID completo (phone@s.whatsapp.net)
                jid = to_whatsapp_jid(normalized)
                jids.append({"jid": jid})
            except Exception as e:
                logger.warning(f"Erro ao normalizar número '{phone}': {e}")
                # Tenta usar como está se já for um JID
                if "@" in phone:
                    jids.append({"jid": phone})
        
        if not jids:
            raise ValueError("Nenhum número válido fornecido para verificação")
        
        logger.info(f"Verificando integridade de {len(jids)} contatos")
        logger.debug(f"JIDs: {[j['jid'] for j in jids]}")
        
        # Cria query
        query = {
            "variables": {
                "input": {
                    "query_input": jids,
                    "telemetry": {
                        "context": "INTERACTIVE"
                    }
                }
            }
        }
        
        # Cria entidade WMEX query
        entity = WmexQueryIqProtocolEntity(
            query_name="BizIntegrityQuery",
            query_obj=query
        )
        iq_node = entity.to_protocol_node()
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de integrity check"""
            try:
                iq_type = node.get_attribute("type")
                
                if iq_type == "error":
                    error_text = "Erro desconhecido"
                    error_node = None
                    for child in node.children:
                        if child.tag == "error":
                            error_node = child
                            break
                    
                    if error_node:
                        error_text = error_node.get_attribute("text") or error_text
                    
                    future.set_exception(Exception(f"Erro ao verificar integridade: {error_text}"))
                    return
                
                if iq_type != "result":
                    future.set_exception(Exception(f"Resposta inválida: tipo={iq_type}"))
                    return
                
                # Processa resultado usando WmexResultIqProtocolEntity
                result_entity = WmexResultIqProtocolEntity.from_protocol_node(node)
                
                if not result_entity:
                    future.set_exception(Exception("Não foi possível processar resultado"))
                    return
                
                # Retorna result_obj
                future.set_result(result_entity.result_obj or {})
                
            except Exception as e:
                logger.error(f"Erro ao processar resposta de integrity check: {e}", exc_info=True)
                future.set_exception(e)
        
        # Registra callback
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        
        # Envia IQ
        try:
            await self._send_iq(iq_node)
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception(f"Erro ao enviar IQ de integrity check: {e}")
        
        # Aguarda resposta
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando resposta de integrity check")
        except Exception as e:
            self._iq_processor.unregister_callback(iq_id)
            raise
