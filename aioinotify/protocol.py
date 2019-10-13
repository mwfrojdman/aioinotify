import asyncio
import os
from pathlib import Path
import logging
from typing import Callable, Dict

from .bindings import INOTIFY_EVENT_SIZE, InotifyEventStructure, add_watch, rm_watch
from .events import InotifyEvent, InotifyFlag

logger = logging.getLogger(__name__)


class InotifyProtocol(asyncio.StreamReaderProtocol):
    def __init__(self, loop, pipe):
        super().__init__(asyncio.StreamReader(loop=loop), loop=loop)
        self._pipe = pipe
        self._watches: Dict[int, Callable[[InotifyEvent], None]] = {}

    async def read_notification(self) -> InotifyEvent:
        logger.debug("Waiting to read %d bytes for next event", INOTIFY_EVENT_SIZE)
        event_data = await self._stream_reader.readexactly(INOTIFY_EVENT_SIZE)
        event = InotifyEventStructure.from_buffer_copy(event_data)
        if event.len > 0:
            raw_name = await self._stream_reader.readexactly(event.len)
            # Linux seems to pad the file paths to at least 16 bytes, even when the actual string
            # is shorter
            raw_name = raw_name.rstrip(b'\x00')
            name = os.fsdecode(raw_name)
        else:
            name = None
        return InotifyEvent(name, event)

    async def dispatch_events(self):
        try:
            while True:
                event = await self.read_notification()
                try:
                    callback = self._watches[event.event.wd]
                except KeyError:
                    logger.info('Unknown watch %s', event.event.wd)
                else:
                    callback(event)
        except asyncio.CancelledError:
            logger.debug("Dispatcher cancelled")
            raise
        except Exception:
            logger.exception("Exception in dispatch_event")
            raise

    def add_watch(self, path: Path, mask: int, callback: Callable[[InotifyEvent], None]) -> int:
        watch_descriptor = add_watch(fd=self._pipe.fileno(), path=path, mask=mask)
        self._watches[watch_descriptor] = callback
        return watch_descriptor

    def remove_watch(self, watch_descriptor: int) -> None:
        rm_watch(self._pipe.fileno(), watch_descriptor)
        del self._watches[watch_descriptor]
