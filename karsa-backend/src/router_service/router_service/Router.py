import socketio
from aiohttp import web
import aiohttp_cors
from karsalib.server import BaseServerNamespace
from karsalib.util import parse_cmd_args


class RouterNamespace(BaseServerNamespace):
    def on_register_namespace(self, sid, namespace):
        print("on_register_namespace")
        global sio
        if not namespace.startswith('/'):
            namespace = '/' + namespace
        if namespace in sio.namespace_handlers:
            print("Namespace %s already registered" %namespace)
            return
        sio.register_namespace( RouterNamespace(namespace) )
        print("Namespace %s registered" %namespace)


def run():
    global sio

    args = parse_cmd_args()
    sio = socketio.AsyncServer(async_mode='aiohttp',
                               cors_allowed_origins='*',
                               ping_timeout=60)
    sio.register_namespace(RouterNamespace('/'))
    app = web.Application()
    sio.attach(app)
    cors = aiohttp_cors.setup(app)
    for resource in app.router._resources:
        if resource.raw_match("/socket.io/"):
            continue
        cors.add(resource,
                 {'*': aiohttp_cors.ResourceOptions(allow_credentials=True, 
                                                    expose_headers="*", 
                                                    allow_headers="*")
                  }
                )
    web.run_app(app, host=args['url'], port=args['port'])


if __name__=='__main__':
    sio = None
    run()   