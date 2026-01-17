"""
Testes unitários para AsyncEventEmitter.
"""

import pytest
import asyncio
from zowpy.core.events import AsyncEventEmitter, EventTimeoutError


@pytest.mark.asyncio
async def test_event_emitter_on_emit():
    """Testa registro e emissão de eventos"""
    emitter = AsyncEventEmitter()
    results = []
    
    async def handler(data):
        results.append(data)
    
    emitter.on("test", handler)
    await emitter.emit("test", "data1")
    await emitter.emit("test", "data2")
    
    assert len(results) == 2
    assert results == ["data1", "data2"]


@pytest.mark.asyncio
async def test_event_emitter_once():
    """Testa handler que executa uma vez"""
    emitter = AsyncEventEmitter()
    results = []
    
    async def handler(data):
        results.append(data)
    
    emitter.once("test", handler)
    await emitter.emit("test", "data1")
    await emitter.emit("test", "data2")
    
    assert len(results) == 1
    assert results == ["data1"]


@pytest.mark.asyncio
async def test_event_emitter_wait_for():
    """Testa wait_for evento"""
    emitter = AsyncEventEmitter()
    
    # Emite evento após delay
    async def delayed_emit():
        await asyncio.sleep(0.1)
        await emitter.emit("test", "data")
    
    asyncio.create_task(delayed_emit())
    
    args, kwargs = await emitter.wait_for("test", timeout=1.0)
    assert args[0] == "data"


@pytest.mark.asyncio
async def test_event_emitter_wait_for_timeout():
    """Testa timeout em wait_for"""
    emitter = AsyncEventEmitter()
    
    with pytest.raises(EventTimeoutError):
        await emitter.wait_for("test", timeout=0.1)


@pytest.mark.asyncio
async def test_event_emitter_off():
    """Testa remoção de handler"""
    emitter = AsyncEventEmitter()
    results = []
    
    async def handler(data):
        results.append(data)
    
    emitter.on("test", handler)
    await emitter.emit("test", "data1")
    
    await emitter.off("test", handler)
    await emitter.emit("test", "data2")
    
    assert len(results) == 1
    assert results == ["data1"]





