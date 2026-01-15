"""
Base Processor - Classe abstrata base para todos os processors.

Cada processor é responsável por processar um tipo específico de protocol node.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode


class BaseProcessor(ABC):
    """
    Classe abstrata base para todos os processors.
    
    Cada processor implementa:
    - can_handle(): Verifica se pode processar um node
    - process(): Processa o node e retorna dados processados
    """
    
    @abstractmethod
    async def can_handle(self, node: ProtocolNode) -> bool:
        """
        Verifica se este processor pode processar o node fornecido.
        
        Args:
            node: Protocol node a verificar
        
        Returns:
            bool: True se pode processar, False caso contrário
        """
        raise NotImplementedError
    
    @abstractmethod
    async def process(
        self, 
        node: ProtocolNode, 
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa o protocol node.
        
        Args:
            node: Protocol node a processar
            raw_data: Dados brutos (bytes) do node (opcional)
        
        Returns:
            Dict com dados processados, ou None se não processou
        """
        raise NotImplementedError
    
    def get_priority(self) -> int:
        """
        Retorna prioridade do processor (maior = processado primeiro).
        
        Útil quando múltiplos processors podem processar o mesmo node.
        Por padrão, retorna 0.
        
        Returns:
            int: Prioridade (padrão: 0)
        """
        return 0

