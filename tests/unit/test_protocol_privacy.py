"""
Testes unitários para protocol/privacy.py
"""

import pytest
import asyncio
from zowpy.protocol.privacy import AsyncPrivacyHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_privacy_handler_init():
    """Testa inicialização do AsyncPrivacyHandler"""
    events = AsyncEventEmitter()
    handler = AsyncPrivacyHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_privacy_handler_handle_iq():
    """Testa processamento de IQ de privacidade"""
    events = AsyncEventEmitter()
    handler = AsyncPrivacyHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("privacy:iq", handler_func)
    
    node = ProtocolTreeNode("iq", {"type": "get"})
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert "node" in received_data[0]


@pytest.mark.asyncio
async def test_async_privacy_handler_send_set_privacy():
    """Testa envio de configurações de privacidade"""
    events = AsyncEventEmitter()
    handler = AsyncPrivacyHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("privacy:set", handler_func)
    
    settings = {"readreceipts": "all", "profile": "contacts"}
    await handler.send_set_privacy(settings)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["settings"] == settings

