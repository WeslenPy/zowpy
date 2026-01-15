"""
Testes unitários para protocol/acks.py
"""

import pytest
import asyncio
from zowpy.protocol.acks import AsyncAcksHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_acks_handler_init():
    """Testa inicialização do AsyncAcksHandler"""
    events = AsyncEventEmitter()
    handler = AsyncAcksHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_acks_handler_handle_ack():
    """Testa processamento de ACK"""
    events = AsyncEventEmitter()
    handler = AsyncAcksHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("ack", handler_func)
    
    node = ProtocolTreeNode("ack", {"id": "123"})
    await handler.handle_ack(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert "node" in received_data[0]
    assert received_data[0]["node"] == node


@pytest.mark.asyncio
async def test_async_acks_handler_send_ack():
    """Testa envio de ACK"""
    events = AsyncEventEmitter()
    handler = AsyncAcksHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("ack:send", handler_func)
    
    message_id = "123"
    jid = "test@whatsapp.net"
    await handler.send_ack(message_id, jid)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["message_id"] == message_id
    assert received_data[0]["jid"] == jid

