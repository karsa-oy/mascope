import socketio
from aiohttp import web
import aiohttp_cors
from karsalib import BaseServerNamespace, parse_cmd_args


class RouterNamespace(BaseServerNamespace):
    pass


def run():
    url, port = parse_cmd_args()
    sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*',
                               ping_timeout=60)
    sio.register_namespace(RouterNamespace('/'))
    sio.register_namespace(RouterNamespace('/tof')) #TODO: Register dynamically
    app = web.Application()
    sio.attach(app)
    cors = aiohttp_cors.setup(app)
    for resource in app.router._resources:
        if resource.raw_match("/socket.io/"):
            continue
        cors.add(resource, { '*': aiohttp_cors.ResourceOptions(allow_credentials=True, 
                                                               expose_headers="*", 
                                                               allow_headers="*") })
    web.run_app(app, host=url, port=port)


if __name__=='__main__':
    run()