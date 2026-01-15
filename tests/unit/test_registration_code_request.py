"""
Testes unitários para registration/code_request.py
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from zowpy.registration.code_request import AsyncCodeRequest


@pytest.mark.asyncio
async def test_async_code_request_init():
    """Testa inicialização do AsyncCodeRequest"""
    request = AsyncCodeRequest("sms", "1234567890")
    assert request.method == "sms"
    assert request.phone_number == "1234567890"
    assert request.url == "https://v.whatsapp.net/v2/code"


@pytest.mark.asyncio
async def test_async_code_request_init_with_config():
    """Testa inicialização com configuração"""
    config = {"mcc": "724", "mnc": "05"}
    request = AsyncCodeRequest("sms", "1234567890", config=config)
    assert request.config == config


@pytest.mark.asyncio
async def test_async_code_request_build_params():
    """Testa construção de parâmetros"""
    request = AsyncCodeRequest("sms", "1234567890")
    params = await request._build_params()
    
    assert "method" in params
    assert params["method"] == "sms"
    assert "mcc" in params
    assert "mnc" in params
    assert "sim_mcc" in params
    assert "sim_mnc" in params
    assert "cellular_strength" in params


@pytest.mark.asyncio
@patch('zowpy.registration.code_request.aiohttp')
async def test_async_code_request_send(mock_aiohttp):
    """Testa envio de requisição de código"""
    # Mock response
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"status": "ok", "code": "123456"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    # Mock session
    mock_session = AsyncMock()
    mock_session.post = Mock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    # Mock ClientSession class
    mock_aiohttp.ClientSession = Mock(return_value=mock_session)
    
    request = AsyncCodeRequest("sms", "1234567890")
    result = await request.send()
    
    assert result["status"] == "ok"
    mock_session.post.assert_called_once()


@pytest.mark.asyncio
@patch('zowpy.registration.code_request.aiohttp', None)
async def test_async_code_request_send_no_aiohttp():
    """Testa envio quando aiohttp não está disponível"""
    request = AsyncCodeRequest("sms", "1234567890")
    
    with pytest.raises(RuntimeError, match="aiohttp não está disponível"):
        await request.send()

