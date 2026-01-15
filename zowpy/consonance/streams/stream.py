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
        while True:
            if self._cancelled.is_set() or self._closed:
                raise StreamCancelledError("Stream cancelled or closed")
            
            try:
                # Aguarda dados - não bloqueia, apenas await
                if timeout is not None:
                    data = await asyncio.wait_for(
                        self._read_queue.get(),
                        timeout=timeout
                    )
                else:
                    data = await self._read_queue.get()
                
                # Poison pill indica cancelamento
                if data is None:
                    raise StreamCancelledError("Stream cancelled")
                
                return data
                
            except asyncio.TimeoutError:
                # Timeout normal, verifica cancelamento
                if self._cancelled.is_set():
                    raise StreamCancelledError("Stream cancelled")
                raise  # Re-raise timeout
    
    async def write_segment(self, data: bytes) -> None:
        """
        Escreve segmento de forma totalmente assíncrona.
        Não bloqueia, apenas adiciona à queue.
        
        Args:
            data: Dados para escrever
        """
        if self._cancelled.is_set() or self._closed:
            return
        
        # Adiciona à queue de escrita para que get_write_segment possa ler
        # (igual ao BlockingQueueSegmentedStream do zowsuplib)
        await self._write_queue.put(data)
        self._write_event.set()
    
    async def get_write_segment(self, timeout: Optional[float] = None) -> bytes:
        """
        Obtém segmento para escrita de forma assíncrona.
        Aguarda dados, não bloqueia.
        
        Args:
            timeout: Timeout em segundos
        
        Returns:
            bytes: Dados para escrever
        
        Raises:
            StreamCancelledError: Se stream foi cancelado
        """
        while True:
            if self._cancelled.is_set() or self._closed:
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
                    raise StreamCancelledError("Stream cancelled")
                
                return data
                
            except asyncio.TimeoutError:
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
            return
        
        await self._read_queue.put(data)
        self._read_event.set()
    
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


