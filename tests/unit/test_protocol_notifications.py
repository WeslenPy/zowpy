"""
Testes unitários para protocol/notifications.py
"""

import pytest
import asyncio
from zowpy.protocol.notifications import AsyncNotificationsHandler
from zowpy.protocol.nodes import ProtocolTreeNode
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_notifications_handler_init():
    """Testa inicialização do AsyncNotificationsHandler"""
    events = AsyncEventEmitter()
    handler = AsyncNotificationsHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_notifications_handler_handle_notification():
    """Testa processamento de notificação"""
    events = AsyncEventEmitter()
    handler = AsyncNotificationsHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("notification", handler_func)
    
    node = ProtocolTreeNode("notification", {"type": "test"})
    await handler.handle_notification(node)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0]["type"] == "test"
    assert received_data[0]["node"] == node

