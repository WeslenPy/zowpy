"""
Async Message Handler - Handler de mensagens totalmente assíncrono.

Processa mensagens recebidas de forma assíncrona usando protobuf estilo whatsmeow.
"""

import asyncio
from typing import Optional, Callable, Dict, Any
from loguru import logger

from ..core.events import AsyncEventEmitter
from ..proto.messages import AsyncMessageParser, MessageType
from ..protocol.entities.ack import OutgoingAckProtocolEntity


class AsyncMessageHandler:
    """
    Handler de mensagens totalmente assíncrono.
    Processa mensagens recebidas de forma assíncrona usando protobuf.
    """
    
    def __init__(
        self, 
        events: AsyncEventEmitter,
    ):
        """
        :param events: Emissor de eventos assíncrono
        :param send_ack_fn: Função async para enviar ack (opcional)
        """
        self.events = events
        self.parser = AsyncMessageParser()
    
    async def handle_message(
        self, 
        message_data: bytes, 
        from_jid: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> None:
        """
        Processa mensagem de forma totalmente assíncrona.
        
        Usa AsyncMessageParser estilo whatsmeow para parsing.
        
        Args:
            message_data: Dados da mensagem (protobuf serializado)
            from_jid: JID do remetente (opcional, pode vir do protocolo)
            message_id: ID da mensagem (opcional, necessário para enviar ack)
        """
        try:


            
            # Parse mensagem usando parser assíncrono estilo whatsmeow
            parsed = await self.parser.parse(message_data)
            
            # Se parsing falhou ou retornou None, cria estrutura básica
            if parsed is None:
                parsed = {}
            
            # Emite evento com dados parseados - await, não bloqueia
            # Formato estilo whatsmeow: inclui from, jid, type, text, etc.
            message_dict: Dict[str, Any] = {
                "type": parsed.get("type", "unknown"),
                "message_type": parsed.get("type", "unknown"),  # Alias para compatibilidade
                "data": parsed.get("data"),
                "raw": message_data,
            }
            
            # Adiciona informações do remetente
            if from_jid:
                message_dict["from"] = from_jid
                message_dict["jid"] = from_jid  # Alias
            
            # Extrai informações do data parseado
            if parsed.get("data"):
                data = parsed["data"]
                
                # Se for TextMessage (dataclass)
                if hasattr(data, "text"):
                    message_dict["text"] = data.text
                # Se for dict
                elif isinstance(data, dict) and "text" in data:
                    message_dict["text"] = data["text"]
                
                # Extrai outros campos comuns
                if hasattr(data, "caption"):
                    message_dict["caption"] = data.caption
                elif isinstance(data, dict) and "caption" in data:
                    message_dict["caption"] = data["caption"]
                
                # Se tiver from no data
                if hasattr(data, "from"):
                    message_dict["from"] = getattr(data, "from", from_jid)
                    message_dict["jid"] = getattr(data, "from", from_jid)
                elif isinstance(data, dict) and "from" in data:
                    message_dict["from"] = data.get("from", from_jid)
                    message_dict["jid"] = data.get("from", from_jid)
            
            await self.events.emit("message", message_dict)
            
            # Envia ack de delivery se send_ack_fn estiver disponível
            if from_jid and message_id and self.send_ack_fn:
                await self.send_delivery_ack(
                    message_id=message_id,
                    to_jid=from_jid
                )
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            # Emite evento de erro
            await self.events.emit("message:error", {
                "error": str(e),
                "raw": message_data,
            })
 
    
    def _deserialize_message(self, message_data: bytes) -> Dict[str, Any]:
        """
        Deserializa mensagem de forma síncrona (para testes).
        
        Args:
            message_data: Dados da mensagem (protobuf serializado)
        
        Returns:
            Dicionário com dados da mensagem
        """
        try:
            # Tenta parsear usando parser síncrono se disponível
            # Por enquanto retorna estrutura básica
            return {
                "data": message_data,
                "type": "unknown",
                "raw": message_data,
            }
        except Exception as e:
            logger.error(f"Erro ao deserializar mensagem: {e}")
            return {
                "data": None,
                "type": "error",
                "raw": message_data,
                "error": str(e),
            }

