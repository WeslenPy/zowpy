"""
Testes unitários para protocol/auth.py
"""

import pytest
import asyncio
from zowpy.protocol.auth import AsyncAuthHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_auth_handler_init():
    """Testa inicialização do AsyncAuthHandler"""
    events = AsyncEventEmitter()
    handler = AsyncAuthHandler(events)
    assert handler.events == events
    assert handler.EVENT_AUTHED == "auth:authed"
    assert handler.EVENT_AUTH == "auth:auth"
    assert handler.EVENT_FAILURE == "auth:failure"
    assert handler.EVENT_SUCCESS == "auth:success"


@pytest.mark.asyncio
async def test_async_auth_handler_handle_stream_features():
    """Testa processamento de stream:features"""
    events = AsyncEventEmitter()
    handler = AsyncAuthHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on(handler.EVENT_STREAM_FEATURES, handler_func)
    
    node = ProtocolTreeNode("stream:features")
    await handler.handle_stream_features(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert "node" in received_data[0]


@pytest.mark.asyncio
async def test_async_auth_handler_handle_success():
    """Testa processamento de sucesso de autenticação"""
    events = AsyncEventEmitter()
    handler = AsyncAuthHandler(events)
    
    success_data = []
    authed_data = []
    
    async def success_handler(data):
        success_data.append(data)
    
    async def authed_handler(data):
        authed_data.append(data)
    
    events.on(handler.EVENT_SUCCESS, success_handler)
    events.on(handler.EVENT_AUTHED, authed_handler)
    
    node = ProtocolTreeNode("success")
    await handler.handle_success(node)
    
    await asyncio.sleep(0.1)
    assert len(success_data) > 0
    assert len(authed_data) > 0


@pytest.mark.asyncio
async def test_async_auth_handler_handle_failure():
    """Testa processamento de falha de autenticação"""
    events = AsyncEventEmitter()
    handler = AsyncAuthHandler(events)
    
    failure_data = []
    disconnect_data = []
    
    async def failure_handler(data):
        failure_data.append(data)
    
    async def disconnect_handler(data):
        disconnect_data.append(data)
    
    events.on(handler.EVENT_FAILURE, failure_handler)
    events.on("connection:disconnect", disconnect_handler)
    
    node = ProtocolTreeNode("failure")
    await handler.handle_failure(node)
    
    await asyncio.sleep(0.1)
    assert len(failure_data) > 0
    assert len(disconnect_data) > 0
    assert disconnect_data[0]["reason"] == "Authentication Failure"


@pytest.mark.asyncio
async def test_async_auth_handler_handle_stream_error():
    """Testa processamento de stream:error"""
    events = AsyncEventEmitter()
    handler = AsyncAuthHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on(handler.EVENT_STREAM_ERROR, handler_func)
    
    node = ProtocolTreeNode("stream:error", {"code": "515"})
    await handler.handle_stream_error(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_auth_handler_send_auth():
    """Testa envio de requisição de autenticação"""
    events = AsyncEventEmitter()
    handler = AsyncAuthHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on(handler.EVENT_AUTH, handler_func)
    
    credentials = {"username": "test", "password": "pass"}
    await handler.send_auth(credentials)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["credentials"] == credentials

