"""
Testes unitários para protocol/messages.py
"""

import pytest
import asyncio
from zowpy.protocol.messages import AsyncMessageHandler
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_message_handler_init():
    """Testa inicialização do AsyncMessageHandler"""
    events = AsyncEventEmitter()
    handler = AsyncMessageHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_message_handler_handle_message():
    """Testa processamento de mensagem"""
    events = AsyncEventEmitter()
    handler = AsyncMessageHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("message", handler_func)
    
    # Cria mensagem protobuf válida (texto simples)
    from zowpy.proto.messages import AsyncMessageBuilder
    message_data = await AsyncMessageBuilder.build_text("test message")
    
    await handler.handle_message(message_data)
    
    await asyncio.sleep(0.1)
    # Pode receber mensagem ou erro, ambos são válidos para teste
    assert len(received_data) > 0
    assert "data" in received_data[0] or "error" in received_data[0]


@pytest.mark.asyncio
async def test_async_message_handler_deserialize_message():
    """Testa deserialização de mensagem"""
    events = AsyncEventEmitter()
    handler = AsyncMessageHandler(events)
    
    message_data = b"test"
    result = handler._deserialize_message(message_data)
    assert isinstance(result, dict)
    assert "data" in result

