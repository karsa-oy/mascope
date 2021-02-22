import socketio
from aiohttp import web
import aiohttp_cors
from karsalib import BaseServerNamespace, parse_cmd_args

# import nest_asyncio
# nest_asyncio.apply()

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

    url, port, _ = parse_cmd_args()
    sio = socketio.AsyncServer(async_mode='aiohttp',
                               cors_allowed_origins='*',
                               ping_timeout=60)
    sio.register_namespace(RouterNamespace('/'))
    # sio.register_namespace(RouterNamespace('/tof')) #TODO: Register dynamically
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
    web.run_app(app, host=url, port=port)


if __name__=='__main__':
    sio = None
    run()   