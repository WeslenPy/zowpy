"""
Clean Dirty IQ - Entidade para limpar estado dirty (account_sync | groups).

Baseado em CleanDirtyIqProtocolEntity do zowsuplib.
"""

import time
from typing import Optional

from .iq import IqProtocolEntity
from ...protocol.structs import ProtocolNode
from ...utils.constants import YowConstants


class CleanDirtyIqProtocolEntity(IqProtocolEntity):
    """
    IQ para limpar dirty (urn:xmpp:whatsapp:dirty).
    type: account_sync | groups
    """

    def __init__(
        self,
        dirty_type: str = "account_sync",
        iq_id: Optional[str] = None,
    ):
        super().__init__(
            xmlns="urn:xmpp:whatsapp:dirty",
            iq_type="set",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER,
        )
        self.dirty_type = dirty_type

    def to_protocol_node(self) -> ProtocolNode:
        node = super().to_protocol_node()
        clean_node = ProtocolNode(
            tag="clean",
            attributes={
                "type": self.dirty_type,
                "timestamp": str(int(time.time())),
            },
            children=[],
        )
        node.children.append(clean_node)
        return node
