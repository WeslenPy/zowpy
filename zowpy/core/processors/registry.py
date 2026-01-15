"""
Processor Registry - Gerencia registro e descoberta de processors.

Facilita o registro automático de processors e fornece utilitários.
"""

from typing import List, Dict, Optional, Type
from loguru import logger

from .base import BaseProcessor
from .router import NodeRouter


class ProcessorRegistry:
    """
    Registry para gerenciar processors.
    
    Permite registro automático e descoberta de processors.
    """
    
    def __init__(self, router: NodeRouter):
        """
        Inicializa registry.
        
        Args:
            router: Router onde processors serão registrados
        """
        self._router = router
        self._processors: Dict[str, BaseProcessor] = {}
    
    def register(self, processor: BaseProcessor, name: Optional[str] = None) -> None:
        """
        Registra um processor no registry e router.
        
        Args:
            processor: Processor a registrar
            name: Nome opcional para o processor (padrão: nome da classe)
        """
        if name is None:
            name = type(processor).__name__
        
        if name in self._processors:
            logger.warning(f"Processor {name} já registrado, substituindo")
        
        self._processors[name] = processor
        self._router.register(processor)
        logger.info(f"Processor {name} registrado no registry")
    
    def unregister(self, name: str) -> None:
        """
        Remove um processor do registry e router.
        
        Args:
            name: Nome do processor a remover
        """
        if name in self._processors:
            processor = self._processors[name]
            self._router.unregister(processor)
            del self._processors[name]
            logger.info(f"Processor {name} removido do registry")
        else:
            logger.warning(f"Processor {name} não encontrado no registry")
    
    def get(self, name: str) -> Optional[BaseProcessor]:
        """
        Obtém um processor por nome.
        
        Args:
            name: Nome do processor
        
        Returns:
            Processor ou None se não encontrado
        """
        return self._processors.get(name)
    
    def get_all(self) -> Dict[str, BaseProcessor]:
        """
        Retorna todos os processors registrados.
        
        Returns:
            Dict com nome → processor
        """
        return self._processors.copy()
    
    def clear(self) -> None:
        """Remove todos os processors"""
        for name in list(self._processors.keys()):
            self.unregister(name)

