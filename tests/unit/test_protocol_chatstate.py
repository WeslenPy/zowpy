"""
Testes unitários para protocol/chatstate.py
"""

import pytest
import asyncio
from zowpy.protocol.chatstate import AsyncChatstateHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_chatstate_handler_init():
    """Testa inicialização do AsyncChatstateHandler"""
    events = AsyncEventEmitter()
    handler = AsyncChatstateHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_chatstate_handler_handle_message_composing():
    """Testa processamento de mensagem com estado 'composing'"""
    events = AsyncEventEmitter()
    handler = AsyncChatstateHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("chatstate", handler_func)
    
    composing_node = ProtocolTreeNode("composing")
    message_node = ProtocolTreeNode("message", children=[composing_node])
    await handler.handle_message(message_node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["type"] == "composing"


@pytest.mark.asyncio
async def test_async_chatstate_handler_handle_message_recording():
    """Testa processamento de mensagem com estado 'recording'"""
    events = AsyncEventEmitter()
    handler = AsyncChatstateHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("chatstate", handler_func)
    
    recording_node = ProtocolTreeNode("recording")
    message_node = ProtocolTreeNode("message", children=[recording_node])
    await handler.handle_message(message_node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["type"] == "recording"


@pytest.mark.asyncio
async def test_async_chatstate_handler_send_composing():
    """Testa envio de estado 'digitando'"""
    events = AsyncEventEmitter()
    handler = AsyncChatstateHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("chatstate:composing", handler_func)
    
    jid = "test@whatsapp.net"
    await handler.send_composing(jid)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["jid"] == jid


@pytest.mark.asyncio
async def test_async_chatstate_handler_send_paused():
    """Testa envio de estado 'pausado'"""
    events = AsyncEventEmitter()
    handler = AsyncChatstateHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("chatstate:paused", handler_func)
    
    jid = "test@whatsapp.net"
    await handler.send_paused(jid)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["jid"] == jid

