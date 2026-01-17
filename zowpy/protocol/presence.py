"""
Async Presence Handler - Handler de presence totalmente assíncrono.
"""

from ..core.events import AsyncEventEmitter


class AsyncPresenceHandler:
    """Handler de presence totalmente assíncrono"""
    
    def __init__(self, events: AsyncEventEmitter):
        self.events = events
    
    async def handle_presence(self, presence_data: bytes) -> None:
        """Processa presence de forma assíncrona"""
        await self.events.emit("presence", presence_data)





