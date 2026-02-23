"""
IB Processor - Processa nós <ib>.

Regras alinhadas ao YowIbProtocolLayer do zowsuplib (recvIb).
"""

from typing import Optional, Dict, Any, Callable, Awaitable
from loguru import logger

from ...protocol.structs import ProtocolNode
from ...protocol.entities.ib import EdgeRoutingIbProtocolEntity
from .base import BaseProcessor


class IbProcessor(BaseProcessor):
    """
    Processa nós <ib>.

    Trata (ordem igual ao zowsuplib):
    - dirty: auto clean (envia CleanDirty IQ se send_node_fn fornecido) e emite ib:dirty
    - offline: emite ib:offline
    - account: emite ib:account
    - edge_routing: emite ib:edge_routing (client pode atualizar profile.config.edge_routing_info)
    - attestation, fbip, notice, safetynet, gpia: ignora (log)
    - offline_preview: log do node
    - demais: warning "Unsupported ib node"
    """

    def __init__(
        self,
        event_emitter=None,
        send_node_fn: Optional[Callable[[ProtocolNode], Awaitable[None]]] = None,
    ):
        """
        Inicializa processor.

        Args:
            event_emitter: EventEmitter para emitir eventos (opcional)
            send_node_fn: Função para enviar node (opcional; usada para auto clean em dirty)
        """
        self._event_emitter = event_emitter
        self._send_node_fn = send_node_fn

    async def can_handle(self, node: ProtocolNode) -> bool:
        """True se é nó <ib>."""
        return node.tag == "ib"

    async def process(self, node: ProtocolNode, raw_data: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        """Processa nó <ib> conforme regras do zowsuplib recvIb."""
        try:
            from_node = node.get_attribute("from")

            # dirty -> auto clean e emite evento
            dirty_child = node.get_child("dirty")
            if dirty_child is not None:
                dirty_type = dirty_child.get_attribute("type") or "account_sync"
                logger.info(f"auto clean {dirty_type}")
                if self._send_node_fn:
                    from ...protocol.entities.iq_clean_dirty import CleanDirtyIqProtocolEntity
                    clean_entity = CleanDirtyIqProtocolEntity(dirty_type=dirty_type)
                    clean_node = clean_entity.to_protocol_node()
                    await self._send_node_fn(clean_node)
                await self._emit_event("ib:dirty", {"type": dirty_type, "from": from_node})
                return {"type": "dirty", "dirty_type": dirty_type}

            # offline
            if node.get_child("offline") is not None:
                await self._emit_event("ib:offline", {"from": from_node})
                return {"type": "offline"}

            # account
            if node.get_child("account") is not None:
                await self._emit_event("ib:account", {"from": from_node})
                return {"type": "account"}

            # edge_routing
            if node.get_child("edge_routing") is not None:
                entity = EdgeRoutingIbProtocolEntity.from_protocol_node(node)
                event_data = {
                    "routing_info": entity.routing_info,
                    "from": from_node,
                }
                logger.info(f"Recebido edge_routing de {from_node}")
                await self._emit_event("ib:edge_routing", event_data)
                return event_data

            # attestation, fbip, notice, safetynet, gpia -> ignorar
            if node.get_child("attestation") is not None:
                logger.info("ignoring attestation ib node")
                return {"type": "attestation", "ignored": True}
            if node.get_child("fbip") is not None:
                logger.info("ignoring fbip ib node")
                return {"type": "fbip", "ignored": True}
            if node.get_child("notice") is not None:
                logger.info("ignoring notice ib node")
                return {"type": "notice", "ignored": True}
            if node.get_child("safetynet") is not None:
                logger.info("ignoring safetynet ib node")
                return {"type": "safetynet", "ignored": True}
            if node.get_child("gpia") is not None:
                logger.info("ignoring gpia ib node")
                return {"type": "gpia", "ignored": True}

            # offline_preview
            if node.get_child("offline_preview") is not None:
                logger.info(f"ib offline_preview: {node}")
                return {"type": "offline_preview"}

            # não suportado
            logger.warning(f"Unsupported ib node: {node}")
            return None

        except Exception as e:
            logger.error(f"Erro ao processar nó <ib>: {e}", exc_info=True)
            return None

    async def _emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Emite evento se event_emitter estiver disponível."""
        if self._event_emitter:
            try:
                await self._event_emitter.emit(event_name, data)
            except Exception as e:
                logger.error(f"Erro ao emitir evento {event_name}: {e}")
