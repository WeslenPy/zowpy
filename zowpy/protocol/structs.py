"""
Protocol Structures - Estruturas simples para protocolo WhatsApp.

Estrutura moderna e simples, sem dependências complexas.
"""

from dataclasses import dataclass, field
import random
from typing import Optional, Dict, List, Any, Union


@dataclass
class ProtocolNode:
    """
    Node de protocolo simples e moderno.
    Substitui ProtocolTreeNode com estrutura mais limpa.
    """

    __ID_GEN = 0
    ID_TYPE_ANDROID = 0
    ID_TYPE_IOS = 1

    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List['ProtocolNode'] = field(default_factory=list)
    data: Optional[bytes] = None

    @staticmethod
    def _generateId(short: bool = False, type: int = ID_TYPE_ANDROID) -> str:
        """
        Gera ID único seguindo padrão do ProtocolEntity do zowsuplib.
        
        Baseado em ProtocolEntity._generateId() do zowsuplib.
        
        Args:
            short: Não usado (mantido para compatibilidade)
            type: Tipo de ID (ID_TYPE_ANDROID ou ID_TYPE_IOS)
        
        Returns:
            String com ID gerado
        """
        if type == ProtocolNode.ID_TYPE_IOS:
            alp = '0123456789ABCDEF0123456789ABCDEF'
            id = ''.join(random.sample(alp, 18))
            id = "3A" + id
        elif type == ProtocolNode.ID_TYPE_ANDROID:
            alp = '0123456789ABCDEF0123456789ABCDEF'
            id = ''.join(random.sample(alp, 32))
        else:
            # Fallback para Android se tipo inválido
            alp = '0123456789ABCDEF0123456789ABCDEF'
            id = ''.join(random.sample(alp, 32))
        
        return id
    
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
        
    def add_child(self, childNode):
        self.children.append(childNode)

    def add_children(self, children):
        for c in children:
            self.add_child(c)
    
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

