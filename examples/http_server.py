import asyncio
import json
from aiohttp import web
from aioinotify.protocol import connect_inotify


@asyncio.coroutine
def handle(request):
    path = request.match_info.get('path')

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'

    @asyncio.coroutine
    def callback(event):
        data = 'data: {}\r\n\r\n'.format(json.dumps(str(event)))
        response.write(data.encode('utf-8'))
        yield from response.drain()

    response.start(request)

    transport, inotify = yield from connect_inotify()
    watch = yield from inotify.watch(callback, path, all_events=True)
    try:
        yield from inotify.close_event.wait()
    finally:
        watch.close()


@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/{path}', handle)

    srv = yield from loop.create_server(app.make_handler(),
                                        '127.0.0.1', 8080)
    print("Server started at http://127.0.0.1:8080")
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
