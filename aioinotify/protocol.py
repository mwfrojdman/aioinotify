import asyncio
from asyncio.futures import Future
import sys
import logging
from traceback import format_exc

from .bindings import INOTIFY_EVENT_SIZE, InotifyEventStructure, add_watch, rm_watch, init
from .watch import Watch
from .events import InotifyEvent, InotifyMask
from .transport import InotifyTransport


logger = logging.getLogger(__name__)


class InotifyProtocol(asyncio.StreamReaderProtocol):
    def __init__(self, loop, pipe):
        super().__init__(asyncio.StreamReader(loop=loop), loop=loop)
        self._pipe = pipe
        self.disconnected = False
        self._watches = {}
        self._worker = None
        self._closed = False
        self.close_event = asyncio.Event(loop=loop)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def connection_made(self, transport):
        super().connection_made(transport)
        self.transport = transport

    def connection_lost(self, exc):
        self.close()
        super().connection_lost(exc)

    def close(self):
        if not self._closed:
            self.close_event.set()
            self._closed = True
            if self.transport is not None:
                self.transport.close()

    @asyncio.coroutine
    def close_and_wait(self):
        self.close()
        return (yield from self._worker)

    @asyncio.coroutine
    def start(self):
        self._worker = asyncio.async(self.run())

    @asyncio.coroutine
    def _read_notification(self):
        event_data = yield from self._stream_reader.readexactly(INOTIFY_EVENT_SIZE)
        event = InotifyEventStructure.from_buffer_copy(event_data)
        if event.len > 0:
            raw_name = yield from self._stream_reader.readexactly(event.len)
            encoding = sys.getfilesystemencoding()
            name = raw_name.decode(encoding)
        else:
            name = None
        return InotifyEvent(name, event)

    @asyncio.coroutine
    def run(self):
        while not self.close_event.is_set():
            try:
                event = yield from self._read_notification()
                yield from self.dispatch_event(event)
            except Exception:
                logger.error(format_exc())

    @asyncio.coroutine
    def dispatch_event(self, event):
        try:
            watch = self._watches[event.wd]
        except KeyError:
            logger.info('Unknown watch %s', event.wd)
        else:
            yield from watch.dispatch_event(event)

    @asyncio.coroutine
    def watch(self, callback, pathname, all_events=False, **kwargs):
        if all_events:
            for member in InotifyMask:
                kwargs[member.name] = True
        watch_descriptor = add_watch(self._pipe.fileno(), pathname, **kwargs)
        watch = Watch(watch_descriptor, callback, self)
        self._watches[watch_descriptor] = watch
        return watch

    def _remove_watch(self, watch_descriptor):
        self._watches.pop(watch_descriptor)
        rm_watch(self._pipe.fileno(), watch_descriptor)


@asyncio.coroutine
def connect_inotify():
    loop = asyncio.get_event_loop()
    pipe = init(nonblock=True)
    logger.debug('fd is %s', pipe.fileno())

    protocol = InotifyProtocol(loop, pipe)
    waiter = Future(loop=loop)
    transport = InotifyTransport(loop, pipe, protocol, waiter)
    yield from waiter
    yield from protocol.start()

    return transport, protocol
