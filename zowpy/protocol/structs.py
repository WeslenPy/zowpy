"""
Protocol Structures - Estruturas simples para protocolo WhatsApp.

Estrutura moderna e simples, sem dependências complexas.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Union


@dataclass
class ProtocolNode:
    """
    Node de protocolo simples e moderno.
    Substitui ProtocolTreeNode com estrutura mais limpa.
    """
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List['ProtocolNode'] = field(default_factory=list)
    data: Optional[bytes] = None
    
    def get_attribute(self, key: str) -> Optional[str]:
        """Obtém atributo do node."""
        return self.attributes.get(key)
    
    def get_child(self, index_or_tag: Union[int, str]) -> Optional['ProtocolNode']:
        """Obtém filho do node por índice ou tag."""
        if isinstance(index_or_tag, int):
            if 0 <= index_or_tag < len(self.children):
                return self.children[index_or_tag]
            return None
        else:
            # Busca por tag
            for child in self.children:
                if isinstance(child, ProtocolNode) and child.tag == index_or_tag:
                    return child
            return None
    
    def has_children(self) -> bool:
        """Verifica se tem filhos."""
        return len(self.children) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte node para dicionário."""
        return {
            "tag": self.tag,
            "attributes": self.attributes,
            "children": [child.to_dict() for child in self.children],
            "data": self.data.hex() if self.data else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProtocolNode':
        """Cria node a partir de dicionário."""
        children = [cls.from_dict(c) for c in data.get("children", [])]
        node_data = bytes.fromhex(data["data"]) if data.get("data") else None
        return cls(
            tag=data["tag"],
            attributes=data.get("attributes", {}),
            children=children,
            data=node_data,
        )

