"""
Testes unitários para protocol/profiles.py
"""

import pytest
import asyncio
from zowpy.protocol.profiles import AsyncProfilesHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_profiles_handler_init():
    """Testa inicialização do AsyncProfilesHandler"""
    events = AsyncEventEmitter()
    handler = AsyncProfilesHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_profiles_handler_handle_iq():
    """Testa processamento de IQ de perfis"""
    events = AsyncEventEmitter()
    handler = AsyncProfilesHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("profiles:iq", handler_func)
    
    node = ProtocolTreeNode("iq", {"type": "get"})
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert "node" in received_data[0]
    assert received_data[0]["node"] == node


@pytest.mark.asyncio
async def test_async_profiles_handler_send_get_profile():
    """Testa envio de requisição para obter perfil"""
    events = AsyncEventEmitter()
    handler = AsyncProfilesHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("profiles:get", handler_func)
    
    jid = "test@whatsapp.net"
    await handler.send_get_profile(jid)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["jid"] == jid

