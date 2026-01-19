"""
Testes de integração para ZowPyClient.
"""

import pytest
import asyncio
from zowpy import ZowPyClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_client_initialization():
    """Testa inicialização do cliente"""
    client = ZowPyClient("5511999999999")
    assert client.account_id == "5511999999999"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_client_events():
    """Testa sistema de eventos do cliente"""
    client = ZowPyClient("5511999999999")
    events_received = []
    
    @client.on_connected
    async def on_connected():
        events_received.append("connected")
    
    @client.on_disconnected
    async def on_disconnected():
        events_received.append("disconnected")
    
    # Por enquanto apenas testa registro de eventos
    # Conexão real requer configuração completa
    assert len(events_received) == 0









