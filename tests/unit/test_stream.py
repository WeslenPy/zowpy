"""
Testes unitários para AsyncSegmentedStream.
"""

import pytest
import asyncio
from zowpy.noise.stream import AsyncSegmentedStream, StreamCancelledError


@pytest.mark.asyncio
async def test_stream_read_write():
    """Testa fila de escrita (write_segment -> get_write_segment)"""
    stream = AsyncSegmentedStream()
    
    # Escreve segmento primeiro
    await stream.write_segment(b"test data")
    
    # Obtém segmento de escrita (deve receber o que foi escrito)
    data = await stream.get_write_segment(timeout=1.0)
    
    assert data == b"test data"


@pytest.mark.asyncio
async def test_stream_timeout():
    """Testa timeout em leitura"""
    stream = AsyncSegmentedStream()
    
    with pytest.raises(asyncio.TimeoutError):
        await stream.read_segment(timeout=0.1)


@pytest.mark.asyncio
async def test_stream_cancel():
    """Testa cancelamento de stream"""
    stream = AsyncSegmentedStream()
    
    # Cancela stream
    await stream.cancel()
    
    # Tentativa de leitura deve falhar
    with pytest.raises(StreamCancelledError):
        await stream.read_segment()


@pytest.mark.asyncio
async def test_stream_put_read_segment():
    """Testa put_read_segment"""
    stream = AsyncSegmentedStream()
    
    # Adiciona segmento lido
    await stream.put_read_segment(b"read data")
    
    # Lê segmento
    data = await stream.read_segment(timeout=1.0)
    assert data == b"read data"









