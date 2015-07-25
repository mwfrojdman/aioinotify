#!/usr/bin/env python3

import sys
import asyncio
from aioinotify import connect_inotify


@asyncio.coroutine
def print_event(event):
    print('Got event: {}'.format(event))


@asyncio.coroutine
def watch_directory(path):
    transport, inotify = yield from connect_inotify()

    with (yield from inotify.watch(print_event, path, all_events=True)):
        print('Printing all file system events in {}'.format(path))
        yield from asyncio.sleep(60.0)

        print('And now his watch is ended')

    inotify.close()
    transport.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(watch_directory(sys.argv[1]))
    loop.close()

