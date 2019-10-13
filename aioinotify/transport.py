"""
This module is essentially copy-paste from the Python 3.7 standard library's
asyncio.unix_events._UnixReadPipeTransport. That can't however be directly used as the inotify pipe
has a different mode.
"""
import selectors
from asyncio import transports, futures, selector_events
import errno
import os
import logging
import warnings


logger = logging.getLogger(__name__)


class InotifyTransport(transports.ReadTransport):

    max_size = 256 * 1024  # max bytes we read in one event loop iteration

    def __init__(self, loop, pipe, protocol, waiter=None, extra=None):
        super().__init__(extra)
        self._extra['pipe'] = pipe
        self._loop = loop
        self._pipe = pipe
        self._fileno = pipe.fileno()
        self._protocol = protocol
        self._closing = False

        mode = os.fstat(self._fileno).st_mode
        if mode != 0o600:
            self._pipe = None
            self._fileno = None
            self._protocol = None
            raise ValueError("Pipe transport is for inotify pipes only.")

        os.set_blocking(self._fileno, False)

        self._loop.call_soon(self._protocol.connection_made, self)
        # only start reading when connection_made() has been called
        self._loop.call_soon(self._loop._add_reader,
                             self._fileno, self._read_ready)
        if waiter is not None:
            # only wake up the waiter when connection_made() has been called
            self._loop.call_soon(futures._set_result_unless_cancelled,
                                 waiter, None)

    def __repr__(self):
        info = [self.__class__.__name__]
        if self._pipe is None:
            info.append('closed')
        elif self._closing:
            info.append('closing')
        info.append(f'fd={self._fileno}')
        selector = getattr(self._loop, '_selector', None)
        if self._pipe is not None and selector is not None:
            polling = selector_events._test_selector_event(
                selector, self._fileno, selectors.EVENT_READ)
            if polling:
                info.append('polling')
            else:
                info.append('idle')
        elif self._pipe is not None:
            info.append('open')
        else:
            info.append('closed')
        return '<{}>'.format(' '.join(info))

    def _read_ready(self):
        try:
            data = os.read(self._fileno, self.max_size)
        except (BlockingIOError, InterruptedError):
            pass
        except OSError as exc:
            self._fatal_error(exc, 'Fatal read error on pipe transport')
        else:
            if data:
                self._protocol.data_received(data)
            else:
                if self._loop.get_debug():
                    logger.info("%r was closed by peer", self)
                self._closing = True
                self._loop._remove_reader(self._fileno)
                self._loop.call_soon(self._protocol.eof_received)
                self._loop.call_soon(self._call_connection_lost, None)

    def pause_reading(self):
        self._loop._remove_reader(self._fileno)

    def resume_reading(self):
        self._loop._add_reader(self._fileno, self._read_ready)

    def set_protocol(self, protocol):
        self._protocol = protocol

    def get_protocol(self):
        return self._protocol

    def is_closing(self):
        return self._closing

    def close(self):
        if not self._closing:
            self._close(None)

    def __del__(self):
        if self._pipe is not None:
            warnings.warn(f"unclosed transport {self!r}", ResourceWarning,
                          source=self)
            self._pipe.close()

    def _fatal_error(self, exc, message='Fatal error on pipe transport'):
        # should be called by exception handler only
        if (isinstance(exc, OSError) and exc.errno == errno.EIO):
            if self._loop.get_debug():
                logger.debug("%r: %s", self, message, exc_info=True)
        else:
            self._loop.call_exception_handler({
                'message': message,
                'exception': exc,
                'transport': self,
                'protocol': self._protocol,
            })
        self._close(exc)

    def _close(self, exc):
        self._closing = True
        self._loop._remove_reader(self._fileno)
        self._loop.call_soon(self._call_connection_lost, exc)

    def _call_connection_lost(self, exc):
        try:
            self._protocol.connection_lost(exc)
        finally:
            self._pipe.close()
            self._pipe = None
            self._protocol = None
            self._loop = None
