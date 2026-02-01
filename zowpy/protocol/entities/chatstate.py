"""
Chatstate Protocol Entities - Entidades de estado de chat (typing/paused).

Baseado em ChatstateProtocolEntity do zowsuplib.
"""

from typing import Optional, List
from .base import ProtocolEntity
from ...protocol.structs import ProtocolNode


class ChatstateProtocolEntity(ProtocolEntity):
    """
    Entidade base para estados de chat <chatstate>.
    """
    
    STATE_COMPOSING = "composing"
    STATE_PAUSED = "paused"
    
    def __init__(self, state: str):
        """
        Args:
            state: Estado do chat (composing ou paused)
        """
        super().__init__(tag="chatstate")
        self._state = state

    def get_state(self) -> str:
        return self._state

    def to_protocol_node(self) -> ProtocolNode:
        node = super().to_protocol_node()
        # Adiciona o estado como um nó filho vazio
        state_node = ProtocolNode(tag=self._state)
        node.children.append(state_node)
        return node


class OutgoingChatstateProtocolEntity(ChatstateProtocolEntity):
    """
    Entidade para estados de chat de saída <chatstate to="...">.
    """
    
    def __init__(self, state: str, to: str, participant: Optional[str] = None):
        """
        Args:
            state: Estado do chat (composing ou paused)
            to: JID do destinatário
            participant: JID do participante (opcional, para grupos)
        """
        super().__init__(state)
        self._to = to
        self._participant = participant

    def to_protocol_node(self) -> ProtocolNode:
        node = super().to_protocol_node()
        node.set_attribute("to", self._to)
        if self._participant:
            node.set_attribute("participant", self._participant)
        return node
