import asyncio


class Watch:
    """Represents an inotify watch as added by InotifyProtocol.watch().

    Calling the close() method stops monitoring for the watch's path for events."""

    def __init__(self, watch_descriptor, callback, protocol):
        """
        :param int watch_descriptor: The watch descriptor as returned by inotify_add_watch
        :param callback: A function with one positional argument (the event object) called when
        an inotify event happens.
        """
        self.watch_descriptor = watch_descriptor
        self._callback = callback
        self._closed = False
        self._protocol = protocol

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @asyncio.coroutine
    def dispatch_event(self, event):
        if not self._closed:
            yield from self._callback(event)

    def close(self):
        if not self._closed:
            self._protocol._remove_watch(self.watch_descriptor)
        self._closed = True
