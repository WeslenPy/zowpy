"""
Async Auth Handler - Handler de autenticação totalmente assíncrono.

Refatora YowAuthenticationProtocolLayer para async, sem dependência de stack.
"""

import asyncio
from typing import Optional, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from .structs import ProtocolNode


class AsyncAuthHandler:
    """
    Handler de autenticação totalmente assíncrono.
    Processa autenticação via eventos assíncronos.
    """

    EVENT_AUTHED = "auth:authed"
    EVENT_AUTH = "auth:auth"
    EVENT_FAILURE = "auth:failure"
    EVENT_SUCCESS = "auth:success"
    EVENT_STREAM_FEATURES = "auth:stream_features"
    EVENT_STREAM_ERROR = "auth:stream_error"

    def __init__(self, events: AsyncEventEmitter):
        """
        :param events: Emissor de eventos assíncrono
        :type events: AsyncEventEmitter
        """
        self.events = events

    async def handle_stream_features(self, node: ProtocolNode) -> None:
        """
        Processa stream:features de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolTreeNode
        """
        # Extrai features do node para log
        features = []
        if hasattr(node, 'children'):
            features = [child.tag for child in node.children]
        elif hasattr(node, 'get_children'):
            features = [child.tag for child in node.get_children()]
        
        logger.info(f"Processando stream:features com {len(features)} features: {features}")
        
        await self.events.emit(self.EVENT_STREAM_FEATURES, {"node": node, "features": features})

    async def handle_success(self, node: ProtocolNode) -> None:
        """
        Processa sucesso de autenticação de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolTreeNode
        """
        logger.info("Autenticação bem-sucedida (success recebido)")
        
        # Log detalhado do success node
        attributes = getattr(node, 'attributes', {})
        logger.debug(f"Success node: tag={node.tag}, attributes={attributes}")
        
        await self.events.emit(self.EVENT_SUCCESS, {"node": node})
        await self.events.emit(self.EVENT_AUTHED, {"node": node})

    async def handle_failure(self, node: ProtocolNode) -> None:
        """
        Processa falha de autenticação de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolTreeNode
        """
        error_code = node.get_attribute("code") if hasattr(node, 'get_attribute') else None
        error_reason = node.get_attribute("reason") if hasattr(node, 'get_attribute') else None
        
        logger.error(f"Falha na autenticação (code: {error_code}, reason: {error_reason})")
        
        # Log detalhado do failure node
        attributes = getattr(node, 'attributes', {})
        logger.error(f"Failure node: tag={node.tag}, attributes={attributes}")
        
        await self.events.emit(self.EVENT_FAILURE, {
            "node": node,
            "code": error_code,
            "reason": error_reason
        })
        await self.events.emit("connection:disconnect", {
            "reason": "Authentication Failure",
            "code": error_code,
            "error_reason": error_reason,
        })

    async def handle_stream_error(self, node: ProtocolNode) -> None:
        """
        Processa stream:error de forma assíncrona.

        :param node: Nó do protocolo
        :type node: ProtocolTreeNode
        """
        code = node.get_attribute("code") if hasattr(node, 'get_attribute') else None
        error_type = node.get_attribute("type") if hasattr(node, 'get_attribute') else None
        
        logger.error(f"Stream error recebido (code: {code}, type: {error_type})")
        
        # Log detalhado
        attributes = getattr(node, 'attributes', {})
        logger.error(f"Stream error node: tag={node.tag}, attributes={attributes}")
        
        if code == "515":
            logger.warning("Stream error 515 - pode ser temporário")
            await self.events.emit(self.EVENT_STREAM_ERROR, {"node": node, "code": code, "type": error_type})
            return

        await self.events.emit(self.EVENT_STREAM_ERROR, {"node": node, "code": code, "type": error_type})

    async def send_auth(self, credentials: dict) -> None:
        """
        Envia requisição de autenticação.

        :param credentials: Credenciais de autenticação
        """
        await self.events.emit(self.EVENT_AUTH, {"credentials": credentials})

