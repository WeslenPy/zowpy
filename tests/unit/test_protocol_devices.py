"""
Testes unitários para protocol/devices.py
"""

import pytest
import asyncio
from zowpy.protocol.devices import AsyncDevicesHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_devices_handler_init():
    """Testa inicialização do AsyncDevicesHandler"""
    events = AsyncEventEmitter()
    handler = AsyncDevicesHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_devices_handler_handle_iq():
    """Testa processamento de IQ de dispositivos"""
    events = AsyncEventEmitter()
    handler = AsyncDevicesHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("devices:iq", handler_func)
    
    node = ProtocolTreeNode("iq", {"type": "get"})
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert "node" in received_data[0]

