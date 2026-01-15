"""
Testes unitários para protocol/calls.py
"""

import pytest
import asyncio
from zowpy.protocol.calls import AsyncCallsHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_calls_handler_init():
    """Testa inicialização do AsyncCallsHandler"""
    events = AsyncEventEmitter()
    handler = AsyncCallsHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_calls_handler_handle_call():
    """Testa processamento de chamada"""
    events = AsyncEventEmitter()
    handler = AsyncCallsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("call", handler_func)
    
    node = ProtocolTreeNode("call", {"id": "123"})
    await handler.handle_call(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert "node" in received_data[0]
    assert received_data[0]["node"] == node

