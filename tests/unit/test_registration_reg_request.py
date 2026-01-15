"""
Testes unitários para registration/reg_request.py
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from zowpy.registration.reg_request import AsyncRegRequest


@pytest.mark.asyncio
async def test_async_reg_request_init():
    """Testa inicialização do AsyncRegRequest"""
    request = AsyncRegRequest("1234567890", "123456")
    assert request.phone_number == "1234567890"
    assert request.code == "123456"
    assert request.url == "https://v.whatsapp.net/v2/register"


@pytest.mark.asyncio
async def test_async_reg_request_init_with_config():
    """Testa inicialização com configuração"""
    config = {"mcc": "724", "mnc": "05"}
    request = AsyncRegRequest("1234567890", "123456", config=config)
    assert request.config == config


@pytest.mark.asyncio
async def test_async_reg_request_build_params():
    """Testa construção de parâmetros"""
    request = AsyncRegRequest("1234567890", "123456")
    params = await request._build_params()
    
    assert "code" in params
    assert params["code"] == "123456"
    assert "mcc" in params
    assert "mnc" in params


@pytest.mark.asyncio
@patch('zowpy.registration.reg_request.aiohttp')
async def test_async_reg_request_send(mock_aiohttp):
    """Testa envio de requisição de registro"""
    # Mock response
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"status": "ok"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    # Mock session
    mock_session = AsyncMock()
    mock_session.post = Mock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    # Mock ClientSession class
    mock_aiohttp.ClientSession = Mock(return_value=mock_session)
    
    request = AsyncRegRequest("1234567890", "123456")
    result = await request.send()
    
    assert result["status"] == "ok"
    mock_session.post.assert_called_once()


@pytest.mark.asyncio
@patch('zowpy.registration.reg_request.aiohttp', None)
async def test_async_reg_request_send_no_aiohttp():
    """Testa envio quando aiohttp não está disponível"""
    request = AsyncRegRequest("1234567890", "123456")
    
    with pytest.raises(RuntimeError, match="aiohttp não está disponível"):
        await request.send()

