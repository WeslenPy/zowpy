"""
Testes unitários para protocol/contacts.py
"""

import pytest
import asyncio
from zowpy.protocol.contacts import AsyncContactsHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_contacts_handler_init():
    """Testa inicialização do AsyncContactsHandler"""
    events = AsyncEventEmitter()
    handler = AsyncContactsHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_contacts_handler_handle_iq_result():
    """Testa processamento de IQ com resultado"""
    events = AsyncEventEmitter()
    handler = AsyncContactsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("contacts:result", handler_func)
    
    node = ProtocolTreeNode("iq", {"type": "result"})
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_contacts_handler_handle_iq_error():
    """Testa processamento de IQ com erro"""
    events = AsyncEventEmitter()
    handler = AsyncContactsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("contacts:error", handler_func)
    
    node = ProtocolTreeNode("iq", {"type": "error"})
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_contacts_handler_send_sync_contacts():
    """Testa envio de requisição para sincronizar contatos"""
    events = AsyncEventEmitter()
    handler = AsyncContactsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("contacts:sync", handler_func)
    
    contacts = ["1234567890", "0987654321"]
    await handler.send_sync_contacts(contacts)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["contacts"] == contacts


@pytest.mark.asyncio
async def test_async_contacts_handler_send_get_contacts():
    """Testa envio de requisição para obter contatos"""
    events = AsyncEventEmitter()
    handler = AsyncContactsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("contacts:get", handler_func)
    
    contacts = ["1234567890"]
    await handler.send_get_contacts(contacts)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["contacts"] == contacts

