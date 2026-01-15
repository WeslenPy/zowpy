"""
Async Event Emitter - Sistema de eventos totalmente não-bloqueante.

- emit(): fire-and-forget
- Sem await em handlers
- Seguro para protocolos, bridges e state machines
"""

import asyncio
from typing import Dict, List, Callable, Optional, Any, Tuple
from loguru import logger


class EventTimeoutError(Exception):
    """Timeout aguardando evento"""
    pass


class AsyncEventEmitter:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._once_handlers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def once(self, event: str, handler: Callable) -> None:
        if event not in self._once_handlers:
            self._once_handlers[event] = []
        self._once_handlers[event].append(handler)

    async def off(self, event: str, handler: Optional[Callable] = None) -> None:
        async with self._lock:
            if handler is None:
                self._handlers.pop(event, None)
                self._once_handlers.pop(event, None)
                return

            if event in self._handlers:
                try:
                    self._handlers[event].remove(handler)
                except ValueError:
                    pass

            if event in self._once_handlers:
                try:
                    self._once_handlers[event].remove(handler)
                except ValueError:
                    pass

    async def emit(self, event: str, *args, **kwargs) -> None:
        """
        Emite evento de forma NÃO-BLOQUEANTE (fire-and-forget).
        Nunca aguarda handlers.
        """

        async with self._lock:
            handlers = self._handlers.get(event, []).copy()
            once_handlers = self._once_handlers.pop(event, []).copy()

        all_handlers = handlers + once_handlers

        for handler in all_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(
                        self._run_async_handler(handler, event, *args, **kwargs)
                    )
                else:
                    asyncio.create_task(
                        self._run_sync_handler(handler, event, *args, **kwargs)
                    )
            except Exception:
                logger.exception(f"Erro ao agendar handler do evento '{event}'")

    async def _run_async_handler(self, handler, event, *args, **kwargs):
        try:
            await handler(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"Erro no handler async do evento '{event}'")

    async def _run_sync_handler(self, handler, event, *args, **kwargs):
        try:
            await asyncio.to_thread(handler, *args, **kwargs)
        except Exception:
            logger.exception(f"Erro no handler sync do evento '{event}'")

    async def wait_for(
        self,
        event: str,
        timeout: Optional[float] = None,
        condition: Optional[Callable] = None
    ) -> Tuple[tuple, dict]:
        """
        Aguarda evento sem bloquear o event loop.
        Seguro contra deadlock.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def handler(*args, **kwargs):
            try:
                if condition and not condition(*args, **kwargs):
                    return

                if not future.done():
                    future.set_result((args, kwargs))
            except Exception:
                logger.exception(f"Erro em wait_for do evento '{event}'")

        self.once(event, handler)

        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            await self.off(event, handler)
            raise EventTimeoutError(f"Timeout aguardando evento '{event}'")

    def listener_count(self, event: str) -> int:
        return (
            len(self._handlers.get(event, [])) +
            len(self._once_handlers.get(event, []))
        )
