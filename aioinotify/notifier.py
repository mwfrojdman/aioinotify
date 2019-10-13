import asyncio
from contextlib import suppress
import logging
from pathlib import Path
from typing import Optional, Set

from .watch import InotifyWatch
from .bindings import init
from .closable_queue import CloseableQueue, QueueClosed
from .events import InotifyFlag, HighLevelEvent
from .protocol import InotifyProtocol
from .transport import InotifyTransport

logger = logging.getLogger(__name__)


class Inotifier:
    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None, buffer_size: int = 2048):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop: asyncio.AbstractEventLoop = loop
        self._protocol: Optional[InotifyProtocol] = None
        self._transport: Optional[InotifyTransport] = None
        self._event_queue: CloseableQueue = CloseableQueue(maxsize=buffer_size, loop=loop)
        self._dropped_events: int = 0
        self._dispatcher: Optional[asyncio.Task] = None
        self._close_event = asyncio.Event(loop=loop)

    async def __aenter__(self):
        if self._protocol is not None:
            raise ValueError("Async context already entered")
        pipe = init(nonblock=True)  # XXX: transport does this now
        logger.warning('pipe.name = %r', pipe.name)
        self._protocol = InotifyProtocol(loop=self._loop, pipe=pipe)
        waiter = self._loop.create_future()
        try:
            self._transport = InotifyTransport(loop=self._loop, pipe=pipe, protocol=self._protocol, waiter=waiter)
            await waiter
            self._dispatcher = self._loop.create_task(self._protocol.dispatch_events())
        except Exception:
            self._transport.close()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._close_event.set()
        if self._transport is not None:
            self._transport.close()
        if self._dispatcher is not None:
            if not self._dispatcher.done():
                self._dispatcher.cancel()
            with suppress(asyncio.CancelledError):
                await self._dispatcher
        pass

    def watch(self, path: Path, flags: Set[InotifyFlag]) -> InotifyWatch:
        return InotifyWatch(path=path, flags=flags, protocol=self._protocol, queue_event=self._queue_event)

    def _queue_event(self, event: HighLevelEvent) -> None:
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped_events += 1

    def __aiter__(self) -> 'Inotifier':
        return self

    async def __anext__(self) -> HighLevelEvent:
        logger.info('Waiting for next event')
        try:
            return await self._event_queue.get()
        except QueueClosed:
            raise StopAsyncIteration
