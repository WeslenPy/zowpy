"""
Async Receipt Handler - Handler de receipts totalmente assíncrono.
"""

from ..core.events import AsyncEventEmitter


class AsyncReceiptHandler:
    """Handler de receipts totalmente assíncrono"""
    
    def __init__(self, events: AsyncEventEmitter):
        self.events = events
    
    async def handle_receipt(self, receipt_data: bytes) -> None:
        """Processa receipt de forma assíncrona"""
        await self.events.emit("receipt", receipt_data)










