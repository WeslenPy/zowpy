"""
IQ Processor - Processa IQs recebidos.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...core.processors.base import BaseProcessor
from ...core.events import AsyncEventEmitter
from ...core.processors.iq_response import IQResponseProcessor


class IQProcessor(BaseProcessor):
    """Processa IQs recebidos"""
    
    def __init__(
        self, 
        events: AsyncEventEmitter, 
        iq_response_processor: Optional[IQResponseProcessor] = None,
        send_node_fn: Optional[callable] = None
    ):
        """
        Inicializa processor.
        
        Args:
            events: Event emitter para emitir eventos
            iq_response_processor: Processor para processar respostas de IQ e chamar callbacks
            send_node_fn: Função async para enviar protocol nodes (usado para responder pong)
        """
        self._events = events
        self._iq_response_processor = iq_response_processor
        self._send_node_fn = send_node_fn
        self._iq_handlers: Dict[str, callable] = {}
    
    def get_priority(self) -> int:
        """IQs têm prioridade alta (podem ser importantes)"""
        return 8
    
    async def can_handle(self, node: ProtocolNode) -> bool:
        """Verifica se é um IQ"""
        return node.tag == "iq"
    
    async def process(
        self,
        node: ProtocolNode,
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa IQ.
        
        Args:
            node: Protocol node do IQ
            raw_data: Dados brutos (não usado)
        
        Returns:
            Dict com dados processados do IQ
        """
        iq_id = node.get_attribute("id")
        iq_type = node.get_attribute("type")
        iq_xmlns = node.get_attribute("xmlns")
        from_jid = node.get_attribute("from")
        to_jid = node.get_attribute("to")
        
        logger.debug(f"Processando IQ: id={iq_id}, type={iq_type}, xmlns={iq_xmlns}, from={from_jid}")
        
        # CORREÇÃO: Responde pong quando recebe ping (xmlns="urn:xmpp:ping")
        # Baseado em zowsuplib: YowIqProtocolLayer.recvIq()
        # if node["xmlns"] == "urn:xmpp:ping":
        #     entity = PongResultIqProtocolEntity(YowConstants.DOMAIN, node["id"])
        #     self.toLower(entity.toProtocolTreeNode())
        if iq_xmlns == "urn:xmpp:ping" and iq_id and self._send_node_fn:
            # Responde com pong (IQ result com mesmo ID)
            from ...utils.constants import YowConstants
            
            pong_node = ProtocolNode(
                tag="iq",
                attributes={
                    "id": iq_id,
                    "type": "result",
                    "to": YowConstants.DOMAIN
                }
            )
            try:
                await self._send_node_fn(pong_node)
                logger.debug(f"Pong enviado em resposta ao ping {iq_id} ")
            except Exception as e:
                logger.error(f"Erro ao enviar pong para ping {iq_id}: {e}", exc_info=True)
            # Retorna dados mesmo após responder pong
            iq_data: Dict[str, Any] = {
                "id": iq_id,
                "type": iq_type,
                "xmlns": iq_xmlns,
                "from": from_jid,
                "to": to_jid,
                "pong_sent": True
            }
            return iq_data
        
        iq_data: Dict[str, Any] = {
            "id": iq_id,
            "type": iq_type,
            "xmlns": iq_xmlns,
            "from": from_jid,
            "to": to_jid,
        }
        
        # CORREÇÃO: Processa resposta de IQ através do IQResponseProcessor para chamar callbacks
        # Isso deve ser feito ANTES de emitir eventos ou chamar handlers
        if self._iq_response_processor and iq_type in ("result", "error"):
            try:
                processed = await self._iq_response_processor.process_iq_response(node)
                if processed:
                    logger.debug(f"IQ {iq_id} processado por IQResponseProcessor (callback chamado)")
                    # Retorna dados mesmo se callback foi chamado, para manter compatibilidade
            except Exception as e:
                logger.error(f"Erro ao processar IQ response para {iq_id}: {e}", exc_info=True)
        
        # Emite evento
        await self._events.emit("iq", iq_data)
        
        # Chama handler específico se existir
        if iq_xmlns and iq_xmlns in self._iq_handlers:
            try:
                await self._iq_handlers[iq_xmlns](node, iq_data)
            except Exception as e:
                logger.error(f"Erro ao processar IQ handler para xmlns {iq_xmlns}: {e}")
        
        return iq_data
    
    def register_handler(self, xmlns: str, handler: callable) -> None:
        """
        Registra handler para um xmlns específico.
        
        Args:
            xmlns: XMLNS do IQ
            handler: Função async que recebe (node, iq_data)
        """
        self._iq_handlers[xmlns] = handler
        logger.debug(f"Handler registrado para IQ xmlns: {xmlns}")

