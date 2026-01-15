"""
Async Segmented Stream - Stream totalmente assíncrono usando asyncio.Queue.

Zero threads, zero bloqueios, apenas await.
"""

import asyncio
from typing import Optional
from loguru import logger


class StreamCancelledError(Exception):
    """Stream foi cancelado"""
    pass


class AsyncSegmentedStream:
    """
    Stream totalmente assíncrono usando asyncio.Queue.
    Zero threads, zero bloqueios, apenas await.
    """
    
    def __init__(self):
        self._read_queue = asyncio.Queue()
        self._write_queue = asyncio.Queue()
        self._cancelled = asyncio.Event()
        self._read_event = asyncio.Event()
        self._write_event = asyncio.Event()
        self._closed = False
    
    async def read_segment(self, timeout: Optional[float] = None) -> bytes:
        """
        Lê segmento de forma totalmente assíncrona.
        Aguarda dados, não bloqueia outras corrotinas.
        
        Args:
            timeout: Timeout em segundos (None = sem timeout)
        
        Returns:
            bytes: Dados lidos
        
        Raises:
            StreamCancelledError: Se stream foi cancelado
            asyncio.TimeoutError: Se timeout excedido
        """
        logger.debug(f"read_segment: aguardando dados (timeout={timeout})")
        while True:
            if self._cancelled.is_set() or self._closed:
                logger.warning("read_segment: stream cancelado ou fechado")
                raise StreamCancelledError("Stream cancelled or closed")
            
            try:
                # Aguarda dados - não bloqueia, apenas await
                if timeout is not None:
                    logger.debug(f"read_segment: aguardando com timeout de {timeout}s")
                    data = await asyncio.wait_for(
                        self._read_queue.get(),
                        timeout=timeout
                    )
                else:
                    logger.debug("read_segment: aguardando sem timeout")
                    data = await self._read_queue.get()
                
                # Poison pill indica cancelamento
                if data is None:
                    logger.warning("read_segment: recebido None (poison pill)")
                    raise StreamCancelledError("Stream cancelled")

                logger.info(f"read_segment: ✓ recebidos {len(data)} bytes da queue")
                logger.debug(f"read_segment: primeiros 50 bytes (hex): {data[:50].hex() if len(data) >= 50 else data.hex()}")
                
                return data
                
            except asyncio.TimeoutError:
                # Timeout normal, verifica cancelamento
                logger.debug(f"read_segment: timeout aguardando dados")
                if self._cancelled.is_set():
                    raise StreamCancelledError("Stream cancelled")
                raise  # Re-raise timeout
    
    async def write_segment(self, data: bytes) -> None:
        """
        Escreve segmento de forma totalmente assíncrona.
        Não bloqueia, apenas adiciona à queue.
        
        Baseado no zowsuplib BlockingQueueSegmentedStream.write_segment()
        
        Args:
            data: Dados para escrever
        """
        if self._cancelled.is_set() or self._closed:
            logger.warning(f"write_segment: stream cancelado, ignorando {len(data)} bytes")
            return
        
        logger.info(f"write_segment: adicionando {len(data)} bytes à write_queue")
        # Adiciona à queue de escrita para que get_write_segment possa ler
        # (igual ao BlockingQueueSegmentedStream do zowsuplib)
        await self._write_queue.put(data)
        self._write_event.set()
        logger.info(f"write_segment: ✓ {len(data)} bytes adicionados à queue (tamanho: {self._write_queue.qsize()})")
        logger.debug(f"write_segment: primeiros 50 bytes (hex): {data[:50].hex() if len(data) >= 50 else data.hex()}")
    
    async def get_write_segment(self, timeout: Optional[float] = None) -> bytes:
        """
        Obtém segmento para escrita de forma assíncrona.
        Aguarda dados, não bloqueia.
        
        Baseado no zowsuplib BlockingQueueSegmentedStream.get_write_segment()
        
        Args:
            timeout: Timeout em segundos
        
        Returns:
            bytes: Dados para escrever
        
        Raises:
            StreamCancelledError: Se stream foi cancelado
        """
        logger.debug(f"get_write_segment: aguardando dados (timeout={timeout})")
        while True:
            if self._cancelled.is_set() or self._closed:
                logger.warning("get_write_segment: stream cancelado ou fechado")
                raise StreamCancelledError("Stream cancelled or closed")
            
            try:
                if timeout is not None:
                    data = await asyncio.wait_for(
                        self._write_queue.get(),
                        timeout=timeout
                    )
                else:
                    data = await self._write_queue.get()
                
                if data is None:
                    logger.warning("get_write_segment: recebido None (poison pill)")
                    raise StreamCancelledError("Stream cancelled")

                logger.info(f"get_write_segment: ✓ recebidos {len(data)} bytes da queue")
                logger.debug(f"get_write_segment: primeiros 50 bytes (hex): {data[:50].hex() if len(data) >= 50 else data.hex()}")
                
                return data
                
            except asyncio.TimeoutError:
                logger.debug(f"get_write_segment: timeout aguardando dados")
                if self._cancelled.is_set():
                    raise StreamCancelledError("Stream cancelled")
                raise
    
    async def put_read_segment(self, data: bytes) -> None:
        """
        Adiciona segmento lido de forma assíncrona.
        
        Args:
            data: Dados lidos
        """
        if self._cancelled.is_set() or self._closed:
            logger.warning(f"put_read_segment: stream cancelado ou fechado, ignorando {len(data)} bytes")
            return
        
        logger.debug(f"put_read_segment: adicionando {len(data)} bytes à read_queue")
        await self._read_queue.put(data)
        self._read_event.set()
        logger.debug(f"put_read_segment: ✓ {len(data)} bytes adicionados à queue (tamanho da queue: {self._read_queue.qsize()})")
    
    async def cancel(self) -> None:
        """
        Cancela stream de forma assíncrona.
        Sinaliza eventos, não bloqueia.
        """
        self._cancelled.set()
        # Adiciona poison pills para desbloquear operações pendentes
        try:
            await self._read_queue.put(None)
        except Exception:
            pass
        try:
            await self._write_queue.put(None)
        except Exception:
            pass
    
    async def close(self) -> None:
        """Fecha stream de forma assíncrona"""
        self._closed = True
        await self.cancel()
    
    def is_cancelled(self) -> bool:
        """Verifica se está cancelado"""
        return self._cancelled.is_set()
    
    def is_closed(self) -> bool:
        """Verifica se está fechado"""
        return self._closed
    
    async def reset(self) -> None:
        """
        Reseta o stream, limpando queues e estado de cancelamento.
        
        Baseado no zowsuplib BlockingQueueSegmentedStream.reset()
        Útil para reutilizar o stream entre tentativas de handshake.
        """
        logger.info("reset: resetando stream (limpando queues e estado)")
        
        # Limpa read queue
        cleared_read = 0
        while not self._read_queue.empty():
            try:
                self._read_queue.get_nowait()
                cleared_read += 1
            except asyncio.QueueEmpty:
                break
        
        # Limpa write queue
        cleared_write = 0
        while not self._write_queue.empty():
            try:
                self._write_queue.get_nowait()
                cleared_write += 1
            except asyncio.QueueEmpty:
                break
        
        # Resetar estado
        self._cancelled.clear()
        self._closed = False
        self._read_event.clear()
        self._write_event.clear()
        
        logger.info(f"reset: ✓ stream resetado (limpos {cleared_read} read, {cleared_write} write)")


