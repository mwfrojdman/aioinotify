"""
This module is essentially copy-paste from the Python 3.4 standard library's
asyncio.unix_events._UnixReadPipeTransport. That can't however be directly used as the inotify pipe
has a different mode.
"""
from asyncio import selectors, transports
import os
import logging
import sys
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
        mode = os.fstat(self._fileno).st_mode
        if mode != 0o600:
            raise ValueError("Inotify pipe transport is for inotify pipes only.")
        self._protocol = protocol
        self._closing = False
        self._loop.call_soon(self._protocol.connection_made, self)
        # only start reading when connection_made() has been called
        self._loop.call_soon(self._loop.add_reader,
                             self._fileno, self._read_ready)
        if waiter is not None:
            # only wake up the waiter when connection_made() has been called
            self._loop.call_soon(self._set_result_unless_cancelled, waiter, None)

    @staticmethod
    def _set_result_unless_cancelled(future, result):
        """Helper setting the result only if the future was not cancelled."""
        if future.cancelled():
            return
        future.set_result(result)

    @staticmethod
    def _test_selector_event(selector, fd, event):
        # Test if the selector is monitoring 'event' events
        # for the file descriptor 'fd'.
        try:
            key = selector.get_key(fd)
        except KeyError:
            return False
        else:
            return bool(key.events & event)

    def __repr__(self):
        info = [self.__class__.__name__]
        if self._pipe is None:
            info.append('closed')
        elif self._closing:
            info.append('closing')
        info.append('fd=%s' % self._fileno)
        if self._pipe is not None:
            polling = self._test_selector_event(
                self._loop._selector,
                self._fileno, selectors.EVENT_READ)
            if polling:
                info.append('polling')
            else:
                info.append('idle')
        else:
            info.append('closed')
        return '<%s>' % ' '.join(info)

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
                self._loop.remove_reader(self._fileno)
                self._loop.call_soon(self._protocol.eof_received)
                self._loop.call_soon(self._call_connection_lost, None)

    def pause_reading(self):
        logger.debug('Pausing reading')
        self._loop.remove_reader(self._fileno)

    def resume_reading(self):
        logger.debug('Resuming reading')
        self._loop.add_reader(self._fileno, self._read_ready)

    def close(self):
        if not self._closing:
            self._close(None)

    # On Python 3.3 and older, objects with a destructor part of a reference
    # cycle are never destroyed. It's not more the case on Python 3.4 thanks
    # to the PEP 442.
    if sys.version_info >= (3, 4):
        def __del__(self):
            if self._pipe is not None:
                warnings.warn("unclosed transport %r" % self, ResourceWarning)
                self._pipe.close()

    def _fatal_error(self, exc, message='Fatal error on pipe transport'):
        logger.debug('Fatal error occurred')
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
        self._loop.remove_reader(self._fileno)
        self._loop.call_soon(self._call_connection_lost, exc)

    def _call_connection_lost(self, exc):
        logger.info('Lost connection: %s', exc)
        try:
            self._protocol.connection_lost(exc)
        finally:
            self._pipe.close()
            self._pipe = None
            self._protocol = None
            self._loop = None
