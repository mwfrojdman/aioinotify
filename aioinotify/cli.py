from contextlib import AsyncExitStack
import logging
from argparse import ArgumentParser
import asyncio
from pathlib import Path
from typing import Iterable

from .notifier import Inotifier
from .events import ALL_FLAGS

logger = logging.getLogger(__name__)


async def _main(paths: Iterable[Path]):
    async with Inotifier() as inotifier, AsyncExitStack() as stack:
        watches = [inotifier.watch(path=path, flags=ALL_FLAGS) for path in paths]
        for watch in watches:
            await stack.enter_async_context(watch)

        async for event in inotifier:
            print(event)
            if event.ignored:
                watches = [watch for watch in watches if not watch.closed]
                if not watches:
                    break


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-ll', '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='WARNING')
    parser.add_argument('paths', nargs='+', help='File path(s) to watch for file system events', type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))

    asyncio.run(_main(args.paths))


if __name__ == '__main__':
    main()
