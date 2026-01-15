"""
Testes unitários para protocol/receipts.py
"""

import pytest
import asyncio
from zowpy.protocol.receipts import AsyncReceiptHandler
from zowpy.core.events import AsyncEventEmitter


@pytest.mark.asyncio
async def test_async_receipt_handler_init():
    """Testa inicialização do AsyncReceiptHandler"""
    events = AsyncEventEmitter()
    handler = AsyncReceiptHandler(events)
    assert handler.events == events


@pytest.mark.asyncio
async def test_async_receipt_handler_handle_receipt():
    """Testa processamento de receipt"""
    events = AsyncEventEmitter()
    handler = AsyncReceiptHandler(events)
    
    received_data = []
    
    async def handler_func(data):
        received_data.append(data)
    
    events.on("receipt", handler_func)
    
    receipt_data = b"test receipt data"
    await handler.handle_receipt(receipt_data)
    
    await asyncio.sleep(0.1)
    assert len(received_data) > 0
    assert received_data[0] == receipt_data

