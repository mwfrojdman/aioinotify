#!/usr/bin/env python3
from pathlib import Path
import sys
import asyncio
from aioinotify.notifier import Inotifier
from aioinotify.events import ALL_FLAGS


async def watch_directory(path):
    """
    Watch for all events in *path* for 60 seconds.
    """
    async with Inotifier() as inotifier:
        async with inotifier.watch(path, mask=ALL_FLAGS):
            print('Printing all file system events in {}'.format(path))
            await asyncio.sleep(60.0)
            print('And now his watch is ended')
            async for event in inotifier:
                print(f"Got event: {event}")


if __name__ == '__main__':
    asyncio.run(watch_directory(Path(sys.argv[1])))
