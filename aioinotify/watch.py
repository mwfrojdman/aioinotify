import functools
import operator
from pathlib import Path
from typing import Set, Callable, Optional

from .events import InotifyFlag, HighLevelEvent, InotifyEvent
from .protocol import InotifyProtocol


class InotifyWatch:
    def __init__(
        self, path: Path, flags: Set[InotifyFlag], protocol: InotifyProtocol, queue_event: Callable[[HighLevelEvent], None],
    ):
        self.path = path
        self._protocol = protocol
        self.flags = flags
        self._mask = functools.reduce(operator.or_, (flag.value for flag in flags))  # no initial, zero mask is forbidden
        self._queue_event = queue_event
        self._wd: Optional[int] = None
        self._closed = False

    @property
    def closed(self):
        return self._closed

    async def __aenter__(self):
        if self._wd is not None:
            raise ValueError('Async context already entered')
        self._wd = self._protocol.add_watch(path=self.path, mask=self._mask, callback=self._callback)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._closed = True
        if self._wd is not None:
            self._protocol.remove_watch(watch_descriptor=self._wd)

    def _callback(self, event: InotifyEvent) -> None:
        if self._closed:
            return
        mask = event.event.mask
        if event.pathname is None:
            path = self.path
        else:
            path = self.path.joinpath(event.pathname)
        self._queue_event(HighLevelEvent(path=path, cookie=event.event.cookie, mask=mask))
        if mask & InotifyFlag.ignored.value != 0:
            self._wd = None  # watch descriptor cannot be removed
            self._closed = True
