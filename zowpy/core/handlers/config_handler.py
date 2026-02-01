"""
Config Handler - Gerencia requisições de configuração e propriedades.

Handler para obter configurações de push e propriedades do servidor.
"""

import asyncio
from typing import Dict, Any, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...protocol.entities.iq_push import PushIqProtocolEntity
from ...protocol.entities.iq_props import PropsIqProtocolEntity
from ..processors.iq_response import IQResponseProcessor


class ConfigHandler:
    """
    Gerencia requisições de configuração.
    
    Equivalente ao getConfig do zowsuplib.
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
    
    async def get_config(self) -> Dict[str, Any]:
        """
        Obtém configurações de push e propriedades do servidor.
        
        Envia PushIq e PropsIq em paralelo.
        
        Returns:
            Dict com resultados das operações
        """
        logger.info("Solicitando configurações do servidor (push e props)...")
        
        # 1. Prepara Push IQ
        push_entity = PushIqProtocolEntity()
        push_node = push_entity.to_protocol_node()
        push_id = push_node.get_attribute("id")
        
        # 2. Prepara Props IQ
        props_entity = PropsIqProtocolEntity()
        props_node = props_entity.to_protocol_node()
        props_id = props_node.get_attribute("id")
        
        # Futures para aguardar respostas
        push_future = asyncio.Future()
        props_future = asyncio.Future()
        
        async def on_push_response(node: ProtocolNode):
            try:
                logger.debug(f"Resposta de Push IQ recebida: {node.get_attribute('type')}")
                push_future.set_result(node)
            except Exception as e:
                if not push_future.done():
                    push_future.set_exception(e)

        async def on_props_response(node: ProtocolNode):
            try:
                logger.debug(f"Resposta de Props IQ recebida: {node.get_attribute('type')}")
                props_future.set_result(node)
            except Exception as e:
                if not props_future.done():
                    props_future.set_exception(e)
        
        # Registra callbacks
        self._iq_processor.register_callback(push_id, on_push_response, timeout=30.0)
        self._iq_processor.register_callback(props_id, on_props_response, timeout=30.0)
        
        # Envia os nodes
        await self._send_iq(push_node)
        await self._send_iq(props_node)
        
        # Aguarda respostas (opcionalmente pode ser fire-and-forget, mas aqui aguardamos)
        try:
            results = await asyncio.gather(
                asyncio.wait_for(push_future, timeout=30.0),
                asyncio.wait_for(props_future, timeout=30.0),
                return_exceptions=True
            )
            
            return {
                "push": results[0] if not isinstance(results[0], Exception) else str(results[0]),
                "props": results[1] if not isinstance(results[1], Exception) else str(results[1])
            }
            
        except Exception as e:
            logger.warning(f"Erro ao aguardar respostas de configuração: {e}")
            return {"error": str(e)}
