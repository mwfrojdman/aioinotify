import logging
from argparse import ArgumentParser
import asyncio

from .protocol import connect_inotify


logger = logging.getLogger(__name__)


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-ll', '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='WARNING')
    parser.add_argument('paths', nargs='+', help='File path(s) to watch for file system events')
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))

    try:
        loop = asyncio.get_event_loop()
        _, inotify = loop.run_until_complete(connect_inotify())
        @asyncio.coroutine
        def run(inotify):
            @asyncio.coroutine
            def callback(event):
                print(event)
            for path in args.paths:
                watch = yield from inotify.watch(callback, path, all_events=True)
                logger.debug('Added watch %s for all events in %s', watch.watch_descriptor, path)
            yield from inotify.close_event.wait()
        try:
            loop.run_until_complete(run(inotify))
        except KeyboardInterrupt:
            inotify.close()
        loop.run_until_complete(inotify.close_event.wait())
    finally:
        loop.close()


if __name__ == '__main__':
    main()
