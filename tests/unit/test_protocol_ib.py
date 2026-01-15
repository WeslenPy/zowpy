"""
Testes unitários para protocol/ib.py
"""

import pytest
import asyncio
from zowpy.protocol.ib import AsyncIBHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_ib_handler_init():
    """Testa inicialização do AsyncIBHandler"""
    events = AsyncEventEmitter()
    handler = AsyncIBHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_ib_handler_handle_iq():
    """Testa processamento de IQ de IB"""
    events = AsyncEventEmitter()
    handler = AsyncIBHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("ib:iq", handler_func)
    
    node = ProtocolTreeNode("iq", {"type": "get"})
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert "node" in received_data[0]

