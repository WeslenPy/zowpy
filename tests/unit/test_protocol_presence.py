"""
Testes unitários para protocol/presence.py
"""

import pytest
import asyncio
from zowpy.protocol.presence import AsyncPresenceHandler
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_presence_handler_init():
    """Testa inicialização do AsyncPresenceHandler"""
    events = AsyncEventEmitter()
    handler = AsyncPresenceHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_presence_handler_handle_presence():
    """Testa processamento de presence"""
    events = AsyncEventEmitter()
    handler = AsyncPresenceHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("presence", handler_func)
    
    presence_data = b"test presence data"
    await handler.handle_presence(presence_data)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0] == presence_data

