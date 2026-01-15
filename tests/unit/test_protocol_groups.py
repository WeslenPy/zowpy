"""
Testes unitários para protocol/groups.py
"""

import pytest
import asyncio
from zowpy.protocol.groups import AsyncGroupsHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_groups_handler_init():
    """Testa inicialização do AsyncGroupsHandler"""
    events = AsyncEventEmitter()
    handler = AsyncGroupsHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_groups_handler_handle_iq_groups():
    """Testa processamento de IQ com lista de grupos"""
    events = AsyncEventEmitter()
    handler = AsyncGroupsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("groups:list_result", handler_func)
    
    groups_node = ProtocolTreeNode("groups")
    node = ProtocolTreeNode("iq", {"type": "result"}, children=[groups_node])
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_groups_handler_handle_iq_group():
    """Testa processamento de IQ com grupo"""
    events = AsyncEventEmitter()
    handler = AsyncGroupsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("groups:result", handler_func)
    
    group_node = ProtocolTreeNode("group")
    node = ProtocolTreeNode("iq", {"type": "result"}, children=[group_node])
    await handler.handle_iq(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_groups_handler_send_create_group():
    """Testa envio de requisição para criar grupo"""
    events = AsyncEventEmitter()
    handler = AsyncGroupsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("groups:create", handler_func)
    
    participants = ["1234567890@whatsapp.net"]
    subject = "Test Group"
    await handler.send_create_group(participants, subject)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["participants"] == participants
    assert received_data[0]["subject"] == subject


@pytest.mark.asyncio
async def test_async_groups_handler_send_list_groups():
    """Testa envio de requisição para listar grupos"""
    events = AsyncEventEmitter()
    handler = AsyncGroupsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("groups:list", handler_func)
    
    await handler.send_list_groups()
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0


@pytest.mark.asyncio
async def test_async_groups_handler_send_add_participants():
    """Testa envio de requisição para adicionar participantes"""
    events = AsyncEventEmitter()
    handler = AsyncGroupsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("groups:add", handler_func)
    
    group_jid = "123456789@g.us"
    participants = ["1234567890@whatsapp.net"]
    await handler.send_add_participants(group_jid, participants)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["group_jid"] == group_jid
    assert received_data[0]["participants"] == participants


@pytest.mark.asyncio
async def test_async_groups_handler_handle_notification_subject():
    """Testa processamento de notificação de mudança de assunto"""
    events = AsyncEventEmitter()
    handler = AsyncGroupsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("groups:subject_notification", handler_func)
    
    subject_node = ProtocolTreeNode("subject")
    node = ProtocolTreeNode("notification", {"type": "w:gp2"}, children=[subject_node])
    await handler.handle_notification(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0

