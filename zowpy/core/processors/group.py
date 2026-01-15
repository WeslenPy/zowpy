"""
Group Processor - Processa notificações de grupo.

Processa notificações de grupo e emite eventos.
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from .base import BaseProcessor


class GroupProcessor(BaseProcessor):
    """
    Processa notificações de grupo.
    
    Processa notificações como:
    - Criação de grupo
    - Adição/remoção de participantes
    - Mudança de assunto
    - etc.
    """
    
    def __init__(self, event_emitter=None):
        """
        Inicializa processor.
        
        Args:
            event_emitter: EventEmitter para emitir eventos (opcional)
        """
        self._event_emitter = event_emitter
    
    async def can_handle(self, node: ProtocolNode) -> bool:
        """
        Verifica se pode processar o node.
        
        Args:
            node: Protocol node
        
        Returns:
            True se é notificação de grupo
        """
        # Verifica se é notificação de grupo
        if node.tag != "notification":
            return False
        
        # Verifica se tem type="w:gp2"
        node_type = node.get_attribute("type")
        if node_type != "w:gp2":
            return False
        
        return True
    
    async def process(self, node: ProtocolNode, raw_data: bytes) -> Optional[Dict]:
        """
        Processa notificação de grupo.
        
        Args:
            node: Protocol node da notificação
            raw_data: Dados brutos (não usado)
        
        Returns:
            Dict com informações da notificação ou None
        """
        try:
            # Obtém node filho (subject, create, remove, add)
            child = node.get_child(0)
            if not child:
                logger.warning("Notificação de grupo sem filho")
                return None
            
            notification_type = child.tag
            group_jid = node.get_attribute("from") or node.get_attribute("to")
            
            event_data = {
                "type": notification_type,
                "group_jid": group_jid,
                "timestamp": node.get_attribute("t") or None
            }
            
            # Processa cada tipo de notificação
            if notification_type == "subject":
                # Mudança de assunto
                subject_data = child.data
                if subject_data:
                    subject = subject_data.decode("utf-8") if isinstance(subject_data, bytes) else subject_data
                    event_data["subject"] = subject
                    event_data["subject_owner"] = child.get_attribute("s_o") or None
                    event_data["subject_time"] = child.get_attribute("s_t") or None
                
                logger.info(f"Assunto do grupo {group_jid} alterado: {event_data.get('subject', '')[:50]}")
                await self._emit_event("group:subject_changed", event_data)
            
            elif notification_type == "create":
                # Criação de grupo ou convite
                reason = child.get_attribute("reason")
                if reason:
                    # É um convite
                    event_data["reason"] = reason
                    event_data["creator"] = child.get_attribute("creator") or None
                    logger.info(f"Convite para grupo {group_jid}: {reason}")
                    await self._emit_event("group:invite", event_data)
                else:
                    # É criação de grupo
                    event_data["creator"] = child.get_attribute("creator") or None
                    event_data["creation"] = child.get_attribute("creation") or None
                    logger.info(f"Grupo {group_jid} criado")
                    await self._emit_event("group:created", event_data)
            
            elif notification_type == "remove":
                # Remoção de participante
                participants = []
                for p_node in child.children:
                    if p_node.tag == "participant":
                        jid = p_node.get_attribute("jid")
                        if jid:
                            participants.append(jid)
                
                event_data["participants"] = participants
                logger.info(f"Participantes removidos do grupo {group_jid}: {len(participants)}")
                await self._emit_event("group:participants_removed", event_data)
            
            elif notification_type == "add":
                # Adição de participante
                participants = []
                for p_node in child.children:
                    if p_node.tag == "participant":
                        jid = p_node.get_attribute("jid")
                        if jid:
                            participants.append(jid)
                
                event_data["participants"] = participants
                logger.info(f"Participantes adicionados ao grupo {group_jid}: {len(participants)}")
                await self._emit_event("group:participants_added", event_data)
            
            else:
                logger.debug(f"Tipo de notificação de grupo não tratado: {notification_type}")
                event_data["raw"] = str(child)
                await self._emit_event("group:notification", event_data)
            
            return event_data
        
        except Exception as e:
            logger.error(f"Erro ao processar notificação de grupo: {e}", exc_info=True)
            return None
    
    async def _emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Emite evento se event_emitter estiver disponível.
        
        Args:
            event_name: Nome do evento
            data: Dados do evento
        """
        if self._event_emitter:
            try:
                await self._event_emitter.emit(event_name, data)
            except Exception as e:
                logger.error(f"Erro ao emitir evento {event_name}: {e}")

