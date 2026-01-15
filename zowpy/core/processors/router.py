"""
Node Router - Roteia protocol nodes para processors apropriados.

Sistema de roteamento baseado em prioridade e capacidade de processamento.
"""

from typing import List, Optional, Dict, Any
from loguru import logger

from ...protocol.structs import ProtocolNode
from .base import BaseProcessor


class NodeRouter:
    """
    Roteia protocol nodes para processors corretos.
    
    Sistema baseado em prioridade:
    - Processors com maior prioridade são testados primeiro
    - Primeiro processor que pode processar é usado
    """
    
    def __init__(self):
        """Inicializa router vazio"""
        self._processors: List[BaseProcessor] = []
    
    def register(self, processor: BaseProcessor) -> None:
        """
        Registra um processor no router.
        
        Processors são ordenados por prioridade (maior primeiro).
        
        Args:
            processor: Processor a registrar
        """
        self._processors.append(processor)
        # Ordena por prioridade (maior primeiro)
        self._processors.sort(key=lambda p: p.get_priority(), reverse=True)
        logger.debug(f"Processor {type(processor).__name__} registrado (prioridade: {processor.get_priority()})")
    
    def unregister(self, processor: BaseProcessor) -> None:
        """
        Remove um processor do router.
        
        Args:
            processor: Processor a remover
        """
        if processor in self._processors:
            self._processors.remove(processor)
            logger.debug(f"Processor {type(processor).__name__} removido")
    
    async def route(
        self, 
        node: ProtocolNode, 
        raw_data: Optional[bytes] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Roteia node para processor apropriado.
        
        Testa processors em ordem de prioridade até encontrar um que pode processar.
        
        Args:
            node: Protocol node a rotear
            raw_data: Dados brutos (bytes) do node (opcional)
        
        Returns:
            Dict com dados processados, ou None se nenhum processor processou
        """
        logger.info(f"Roteando node: node={node}, processors registrados={len(self._processors)}")
        logger.debug(f"Roteando node: tag={node.tag}, processors registrados={len(self._processors)}")
        
        for processor in self._processors:
            try:
                # Verifica se pode processar
                if await processor.can_handle(node):
                    logger.debug(f"Processor {type(processor).__name__} pode processar node {node.tag}")
                    # Processa
                    result = await processor.process(node, raw_data)
                    if result is not None:
                        logger.debug(f"Processor {type(processor).__name__} processou node {node.tag} com sucesso")
                        return result
                    else:
                        logger.debug(f"Processor {type(processor).__name__} não processou node {node.tag} (retornou None)")
            except Exception as e:
                logger.error(f"Erro ao processar node {node.tag} com {type(processor).__name__}: {e}", exc_info=True)
                # Continua tentando outros processors
                continue
        
        logger.debug(f"Nenhum processor processou node {node.tag}")
        return None
    
    def get_registered_processors(self) -> List[BaseProcessor]:
        """
        Retorna lista de processors registrados.
        
        Returns:
            Lista de processors (ordenados por prioridade)
        """
        return self._processors.copy()

