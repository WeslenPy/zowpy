"""
Testes unitários para protocol/media.py
"""

import pytest
import asyncio
from zowpy.protocol.media import AsyncMediaHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_media_handler_init():
    """Testa inicialização do AsyncMediaHandler"""
    events = AsyncEventEmitter()
    handler = AsyncMediaHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_media_handler_handle_message_medianotify():
    """Testa processamento de mensagem medianotify"""
    events = AsyncEventEmitter()
    handler = AsyncMediaHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("media:ack", handler_func)
    
    node = ProtocolTreeNode("message", {"type": "medianotify"})
    await handler.handle_message(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_media_handler_handle_message_image():
    """Testa processamento de mensagem de imagem"""
    events = AsyncEventEmitter()
    handler = AsyncMediaHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("media:image", handler_func)
    
    proto_node = ProtocolTreeNode("proto", {"mediatype": "image"})
    node = ProtocolTreeNode("message", {"type": "media"}, children=[proto_node])
    await handler.handle_message(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_media_handler_handle_message_audio():
    """Testa processamento de mensagem de áudio"""
    events = AsyncEventEmitter()
    handler = AsyncMediaHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("media:audio", handler_func)
    
    proto_node = ProtocolTreeNode("proto", {"mediatype": "audio"})
    node = ProtocolTreeNode("message", {"type": "media"}, children=[proto_node])
    await handler.handle_message(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_media_handler_handle_message_video():
    """Testa processamento de mensagem de vídeo"""
    events = AsyncEventEmitter()
    handler = AsyncMediaHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("media:video", handler_func)
    
    proto_node = ProtocolTreeNode("proto", {"mediatype": "video"})
    node = ProtocolTreeNode("message", {"type": "media"}, children=[proto_node])
    await handler.handle_message(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_media_handler_handle_iq():
    """Testa processamento de IQ de mídia"""
    events = AsyncEventEmitter()
    handler = AsyncMediaHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("media:iq_result", handler_func)
    
    node = ProtocolTreeNode("iq", {"type": "result"})
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_media_handler_send_media_connection_request():
    """Testa envio de requisição de conexão de mídia"""
    events = AsyncEventEmitter()
    handler = AsyncMediaHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("media:request_connection", handler_func)
    
    await handler.send_media_connection_request()
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0

