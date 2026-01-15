"""
Testes unitários para api/client.py
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from zowpy.api.client import ZowPyClient
from zowpy.api.errors import ConnectionError, ZowPyError


@pytest.mark.asyncio
async def test_zowpy_client_init():
    """Testa inicialização do cliente"""
    client = ZowPyClient("5511999999999")
    
    assert client.account_id == "5511999999999"
    assert client.db_pool is not None


@pytest.mark.asyncio
async def test_zowpy_client_connect():
    """Testa conexão do cliente"""
    client = ZowPyClient("5511999999999")
    
    # Mock do db_pool
    client.db_pool = AsyncMock()
    client.db_pool.initialize = AsyncMock()
    client.db_pool._pool = MagicMock()
    
    # Mock do WhatsAppClient
    mock_whatsapp_client = AsyncMock()
    mock_whatsapp_client.connect = AsyncMock()
    mock_whatsapp_client.is_connected = MagicMock(return_value=True)
    mock_whatsapp_client.events = MagicMock()
    mock_whatsapp_client.events.on = MagicMock()
    
    with patch("zowpy.api.client.WhatsAppClient", return_value=mock_whatsapp_client):
        await client.connect()
        
        assert client._client is not None
        mock_whatsapp_client.connect.assert_called_once()


@pytest.mark.asyncio
async def test_zowpy_client_connect_error():
    """Testa erro na conexão"""
    client = ZowPyClient("5511999999999")
    
    # Mock do db_pool
    client.db_pool = AsyncMock()
    client.db_pool.initialize = AsyncMock()
    client.db_pool._pool = MagicMock()
    
    # Mock do WhatsAppClient que falha
    with patch("zowpy.api.client.WhatsAppClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client_class.return_value = mock_client
        
        with pytest.raises(ConnectionError):
            await client.connect()


@pytest.mark.asyncio
async def test_zowpy_client_send_text():
    """Testa envio de mensagem de texto"""
    client = ZowPyClient("5511999999999")
    
    # Mock do cliente interno
    mock_whatsapp_client = AsyncMock()
    mock_whatsapp_client.is_connected = MagicMock(return_value=True)
    mock_whatsapp_client.send_text = AsyncMock(return_value="msg_123")
    client._client = mock_whatsapp_client
    
    # Envia mensagem
    message_id = await client.send_text("5511888888888", "Hello!")
    
    assert message_id == "msg_123"
    mock_whatsapp_client.send_text.assert_called_once_with("5511888888888", "Hello!")


@pytest.mark.asyncio
async def test_zowpy_client_send_text_not_connected():
    """Testa envio sem estar conectado"""
    client = ZowPyClient("5511999999999")
    
    with pytest.raises(ConnectionError, match="Not connected"):
        await client.send_text("5511888888888", "Hello!")


@pytest.mark.asyncio
async def test_zowpy_client_wait_for_message():
    """Testa aguardar mensagem"""
    client = ZowPyClient("5511999999999")
    
    # Mock do events
    mock_events = AsyncMock()
    mock_events.wait_for = AsyncMock(return_value=([{"text": "Hello", "from": "5511888888888"}], {}))
    client._events = mock_events
    
    # Aguarda mensagem
    message = await client.wait_for_message(timeout=1.0)
    
    assert message["text"] == "Hello"
    mock_events.wait_for.assert_called_once()


@pytest.mark.asyncio
async def test_zowpy_client_wait_for_message_with_filters():
    """Testa aguardar mensagem com filtros"""
    client = ZowPyClient("5511999999999")
    
    # Mock do events
    mock_events = AsyncMock()
    mock_events.wait_for = AsyncMock(return_value=([{"text": "Hello", "from": "5511888888888@s.whatsapp.net"}], {}))
    client._events = mock_events
    
    # Aguarda mensagem com filtros
    message = await client.wait_for_message(
        timeout=1.0,
        from_jid="5511888888888",
        message_type="text"
    )
    
    assert message["text"] == "Hello"
    mock_events.wait_for.assert_called_once()


@pytest.mark.asyncio
async def test_zowpy_client_wait_for_message_timeout():
    """Testa timeout ao aguardar mensagem"""
    client = ZowPyClient("5511999999999")
    
    # Mock do events que levanta timeout
    from zowpy.core.events import EventTimeoutError
    mock_events = AsyncMock()
    mock_events.wait_for = AsyncMock(side_effect=EventTimeoutError("Timeout"))
    client._events = mock_events
    
    with pytest.raises(ZowPyError, match="Timeout"):
        await client.wait_for_message(timeout=0.1)


@pytest.mark.asyncio
async def test_zowpy_client_disconnect():
    """Testa desconexão"""
    client = ZowPyClient("5511999999999")
    
    # Mock do cliente interno
    mock_whatsapp_client = AsyncMock()
    mock_whatsapp_client.disconnect = AsyncMock()
    client._client = mock_whatsapp_client
    
    # Mock do db_pool
    client.db_pool = AsyncMock()
    client.db_pool.close = AsyncMock()
    
    await client.disconnect()
    
    mock_whatsapp_client.disconnect.assert_called_once()
    client.db_pool.close.assert_called_once()


@pytest.mark.asyncio
async def test_zowpy_client_event_handlers():
    """Testa registro de handlers de eventos"""
    client = ZowPyClient("5511999999999")
    
    async def handler():
        pass
    
    # Registra handlers
    client.on_message(handler)
    client.on_connected(handler)
    client.on_disconnected(handler)
    
    # Verifica que foram registrados
    assert "message" in client._events._handlers
    assert "connected" in client._events._handlers
    assert "disconnected" in client._events._handlers

