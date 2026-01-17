"""
Base Protocol Entity - Classe base para todas as entidades de protocolo.

Baseado em ProtocolEntity do zowsuplib, mas usando herança direta de ProtocolNode.
"""

from typing import Optional, Dict, List
from ...protocol.structs import ProtocolNode


class ProtocolEntity(ProtocolNode):
    """
    Classe base para todas as entidades de protocolo.
    
    Herda de ProtocolNode e adiciona métodos auxiliares para construção
    e parsing de nodes, similar ao ProtocolEntity do zowsuplib.
    """
    
    def __init__(
        self,
        tag: str,
        attributes: Optional[Dict[str, str]] = None,
        children: Optional[List[ProtocolNode]] = None,
        data: Optional[bytes] = None
    ):
        """
        Inicializa entidade de protocolo.
        
        Args:
            tag: Tag do node
            attributes: Atributos do node
            children: Filhos do node
            data: Dados binários do node
        """
        super().__init__(
            tag=tag,
            attributes=attributes or {},
            children=children or [],
            data=data
        )
    
    @classmethod
    def from_protocol_node(cls, node: ProtocolNode) -> 'ProtocolEntity':
        """
        Cria entidade a partir de um ProtocolNode existente.
        
        Baseado em ProtocolEntity.fromProtocolTreeNode() do zowsuplib.
        
        Args:
            node: Node do protocolo
            
        Returns:
            Instância da entidade
        """
        return cls(
            tag=node.tag,
            attributes=node.attributes.copy(),
            children=node.children.copy(),
            data=node.data
        )
    
    def to_protocol_node(self) -> ProtocolNode:
        """
        Converte entidade para ProtocolNode.
        
        Baseado em ProtocolEntity.toProtocolTreeNode() do zowsuplib.
        Como já herda de ProtocolNode, apenas retorna self.
        
        Returns:
            ProtocolNode equivalente
        """
        return self
    
    @staticmethod
    def _generate_id(short: bool = False, id_type: int = ProtocolNode.ID_TYPE_ANDROID) -> str:
        """
        Gera ID único seguindo padrão do zowsuplib.
        
        Args:
            short: Não usado (mantido para compatibilidade)
            id_type: Tipo de ID (ID_TYPE_ANDROID ou ID_TYPE_IOS)
            
        Returns:
            String com ID gerado
        """
        return ProtocolNode._generateId(short=short, type=id_type)

