"""
IB Protocol Entities - Entidades para o nó <ib>.
"""

from typing import Optional
from .base import ProtocolEntity
from ...protocol.structs import ProtocolNode


class IbProtocolEntity(ProtocolEntity):
    """
    Entidade base para nós <ib>.
    """
    def __init__(self, tag: str = "ib"):
        super().__init__(tag=tag)


class EdgeRoutingIbProtocolEntity(IbProtocolEntity):
    """
    Entidade para edge_routing dentro de <ib>.
    
    <ib from="s.whatsapp.net">
        <edge_routing>
            <routing_info>
               {{BYTES}}
            </routing_info>
        </edge_routing>
    </ib>
    """
    def __init__(self, routing_info: bytes):
        super().__init__()
        self.routing_info = routing_info

    def to_protocol_node(self) -> ProtocolNode:
        node = super().to_protocol_node()
        
        ri_node = ProtocolNode(tag="routing_info", data=self.routing_info)
        er_node = ProtocolNode(tag="edge_routing", children=[ri_node])
        
        node.children.append(er_node)
        return node

    @classmethod
    def from_protocol_node(cls, node: ProtocolNode) -> 'EdgeRoutingIbProtocolEntity':
        er_node = node.get_child("edge_routing")
        if er_node:
            ri_node = er_node.get_child("routing_info")
            if ri_node and ri_node.data:
                return cls(routing_info=ri_node.data)
        
        raise ValueError("Node does not contain edge_routing/routing_info")
