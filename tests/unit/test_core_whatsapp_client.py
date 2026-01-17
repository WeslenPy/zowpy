"""
Testes unitários para core/whatsapp_client.py
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from zowpy.core.whatsapp_client import WhatsAppClient
from zowpy.protocol.structs import ProtocolNode


@pytest.mark.asyncio
async def test_whatsapp_client_init():
    """Testa inicialização do cliente"""
    from zowpy.utils.constants import YowConstants
    
    client = WhatsAppClient("5511999999999")
    
    assert client.account_id == "5511999999999"
    # CORREÇÃO: Endpoint agora é selecionado aleatoriamente, verifica se está na lista válida
    assert client.endpoint in YowConstants.ENDPOINTS
    assert not client._connected
    assert not client._authenticated


@pytest.mark.asyncio
async def test_whatsapp_client_initialize_components():
    """Testa inicialização de componentes"""
    mock_db_pool = AsyncMock()
    client = WhatsAppClient("5511999999999", db_pool=mock_db_pool)
    
    with patch("zowpy.core.whatsapp_client.AsyncStateStore") as mock_store:
        # AxolotlManager é obtido via AxolotlManagerFactory
        with patch("zowpy.core.whatsapp_client.AxolotlManagerFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_factory_cls.return_value = mock_factory
            mock_factory.get_manager.return_value = MagicMock()

            with patch("zowpy.core.whatsapp_client.AsyncCoder") as mock_coder:
                with patch("zowpy.core.whatsapp_client.AsyncMessageHandler") as mock_msg_handler:
                    await client._initialize_components()

                    assert client.state_store is not None
                    assert client.axolotl_manager is not None
                    assert client.coder is not None
                    assert client.message_handler is not None


@pytest.mark.asyncio
async def test_whatsapp_client_send_text():
    """Testa envio de mensagem de texto"""
    mock_db_pool = AsyncMock()
    client = WhatsAppClient("5511999999999", db_pool=mock_db_pool)
    
    # Mock de componentes necessários
    client._authenticated = True
    client.noise_protocol = AsyncMock()
    client.coder = AsyncMock()
    client.coder.encoder = AsyncMock()
    client.coder.encoder.encode = AsyncMock(return_value=b"encoded")
    client.coder.encode_and_send = AsyncMock()
    
    # Mock do método _send_protocol_node
    client._send_protocol_node = AsyncMock()
    
    # Envia mensagem
    message_id = await client.send_text("5511888888888", "Hello!")
    
    # Verifica que foi chamado
    assert message_id is not None
    client._send_protocol_node.assert_called_once()


@pytest.mark.asyncio
async def test_whatsapp_client_send_text_not_authenticated():
    """Testa envio sem estar autenticado"""
    client = WhatsAppClient("5511999999999")
    
    with pytest.raises(RuntimeError, match="Not authenticated"):
        await client.send_text("5511888888888", "Hello!")


@pytest.mark.asyncio
async def test_whatsapp_client_process_protocol_node():
    """Testa processamento de protocol node"""
    mock_db_pool = AsyncMock()
    client = WhatsAppClient("5511999999999", db_pool=mock_db_pool)
    client._authenticated = True
    
    # Mock handlers
    client.message_handler = AsyncMock()
    client.acks_handler = AsyncMock()
    client.receipts_handler = AsyncMock()
    client.receipts_handler.handle_receipt = AsyncMock()
    client.presence_handler = AsyncMock()
    client.events = AsyncMock()
    client.events.emit = AsyncMock()
    
    # Testa node de mensagem
    message_node = ProtocolNode(tag="message")
    await client._process_protocol_node(message_node)
    client.message_handler.handle_message.assert_called_once()
    
    # Testa node de ack
    ack_node = ProtocolNode(tag="ack")
    await client._process_protocol_node(ack_node)
    client.acks_handler.handle_ack.assert_called_once()
    
    # Testa node de receipt
    receipt_node = ProtocolNode(tag="receipt")
    await client._process_protocol_node(receipt_node)
    # Receipt handler recebe o node (pode ser convertido para bytes internamente)
    client.receipts_handler.handle_receipt.assert_called()
    
    # Testa node de presence
    presence_node = ProtocolNode(tag="presence")
    await client._process_protocol_node(presence_node)
    client.presence_handler.handle_presence.assert_called_once()


@pytest.mark.asyncio
async def test_whatsapp_client_send_keepalive():
    """Testa envio de keepalive"""
    mock_db_pool = AsyncMock()
    client = WhatsAppClient("5511999999999", db_pool=mock_db_pool)
    
    client._authenticated = True
    client._send_protocol_node = AsyncMock()
    
    await client._send_keepalive()
    
    client._send_protocol_node.assert_called_once()
    call_args = client._send_protocol_node.call_args[0][0]
    assert call_args.tag == "iq"
    assert call_args.get_attribute("type") == "get"


@pytest.mark.asyncio
async def test_whatsapp_client_disconnect():
    """Testa desconexão"""
    mock_db_pool = AsyncMock()
    client = WhatsAppClient("5511999999999", db_pool=mock_db_pool)
    
    client._running = True
    client._connected = True
    client._authenticated = True
    
    # Mock de componentes
    client.connection = AsyncMock()
    client.connection.disconnect = AsyncMock()
    # disconnect() fecha store via axolotl_manager._store.close()
    client.axolotl_manager = AsyncMock()
    client.axolotl_manager._store = AsyncMock()
    client.axolotl_manager._store.close = MagicMock()
    client.events = AsyncMock()
    client.events.emit = AsyncMock()
    
    # Mock de tasks
    client._message_loop_task = asyncio.create_task(asyncio.sleep(0))
    client._keepalive_task = asyncio.create_task(asyncio.sleep(0))
    client._bridge_task = asyncio.create_task(asyncio.sleep(0))
    
    await client.disconnect()
    
    assert not client._running
    assert not client._connected
    assert not client._authenticated
    client.connection.disconnect.assert_called_once()
    client.axolotl_manager._store.close.assert_called_once()


@pytest.mark.asyncio
async def test_whatsapp_client_is_connected():
    """Testa verificação de conexão"""
    client = WhatsAppClient("5511999999999")
    
    assert not client.is_connected()
    
    client._connected = True
    client._authenticated = True
    assert client.is_connected()
    
    client._authenticated = False
    assert not client.is_connected()

