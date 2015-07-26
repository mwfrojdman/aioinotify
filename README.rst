inotify library for asyncio
===========================

Requirements
------------
- Python >= 3.4

License
-------
``aioinotify`` is released under the Apache 2 license.

Documentation
-------------
TODO: Link to readthedocs

Getting started
---------------

.. code-block:: python

  import sys
  import asyncio
  from aioinotify import connect_inotify


  @asyncio.coroutine
  def print_event(event):
      print('Got event: {}'.format(event))


  @asyncio.coroutine
  def watch_directory(path):
      """
      Watch for all events in *path* for 60 seconds.
      """
      with (yield from connect_inotify()) as inotify:
          with (yield from inotify.watch(print_event, path, all_events=True)):
              print('Printing all file system events in {}'.format(path))
              yield from asyncio.sleep(60.0)
              print('And now his watch is ended')


  if __name__ == '__main__':
      loop = asyncio.get_event_loop()
      loop.run_until_complete(watch_directory(sys.argv[1]))
      loop.close()

