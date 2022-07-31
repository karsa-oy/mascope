import inspect
from socketio import AsyncNamespace
import socketio
from aiohttp import web
import aiohttp_cors

from .lib.util import parse_cmd_args, get_client_notification_context


class BaseServerNamespace(AsyncNamespace):
    """ socketio server base namespace class """

    def log(self, *arg, **kwarg):
        print(f"[{self.namespace}.{inspect.stack()[1].function}]", *arg, **kwarg)

    async def on_connect(self, sid, environ):
        self.log(sid, "connected to namespace", self.namespace)

    async def on_disconnect(self, sid):
        self.log(sid, "disconnected from namespace", self.namespace)
        # clear the app caches, if any, in all app services
        # TODO:
        # let affected rooms know the client is gone
        for r in self.rooms(sid):
            await self.emit('room_mate_gone', {}, room=r)

    async def on_declare_endpoints(self, sid, data):
        """
        Declare API from a client service by creating a room for each API function.
        API requests are sent thru Router via client_notifications:
        Client->Router->Service
        The API room is used to send this request to only those services,
        which declare corresponding API.
        data: list(app_name=client_name, endpoints)
        """
        app_name = data['app_name']
        endpoints = data['endpoints']
        for e in endpoints:
            self.enter_room(sid, e)
        # self.log(f"{app_name}:{sid} declares endpoints {endpoints}")
        self.log(f"{app_name} stays in rooms: {self.rooms(sid)}")
        await self.emit('service_state', {})

    async def on_enter_room(self, sid, data):
        app_name = data['app_name']
        room = data['room']
        self.enter_room(sid, room)
        self.log(f"{app_name} : {room}")

    def on_leave_room(self, sid, data):
        app_name = data['app_name']
        room = data['room']
        self.leave_room(sid, room)
        self.log(f"{app_name} : {room}")

    async def on_client_notification(self, sid, data):
        """
        client_notifications on corresponding API endpoints are forwarded by Router from requesters
        to providers via corresponding endpoints, where name = endpoint is a property name.
        data: dict(name=endpoint_name, value=endpoint_value, ...)
              other named args are free form, e.g. 
              room, cookies, no_logging, no_data_logging...
        """
        no_logging = data.get('no_logging', False)
        no_data_logging = data.get('no_data_logging', True)
        endpoint = data['name']
        timeout = data.get('timeout')   # defines if call or emit (sync/async) response
        room = data.get('room')
        namespace = data.get('namespace', self.namespace)
        cb = data.pop('callback', None)
        cb_ctx = data.pop('callback_context', None)



        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{endpoint}: ...")
        else:
            self.log(data)

        if 'cookies' not in data:
            data['cookies'] = dict(src_sid=[])
        elif 'src_sid' not in data['cookies']:
            data['cookies']['src_sid']=[]
        cookies = data['cookies']
        src_sids = cookies['src_sid']
        # sids are added to the cookies only by this procedure
        src_sids.append(sid)
        target_room = room if room else endpoint
        context = get_client_notification_context(data)

        async def srv_callback(*arg, **kwarg):
            await self.emit('client_notification_callback',
                            dict(endpoint=endpoint,
                                 cb_name=cb, cb_ctx=cb_ctx,
                                 arg=arg, kwarg=kwarg,
                                 **{**context, 'no_logging': True}),
                            room=sid,
                            namespace=self.namespace
                            )

        sent_to = len(src_sids) * '>'
        self.log(f"{endpoint} {sent_to} {namespace}:{target_room}")
        if timeout is None:     # response to async emit_client_notification
            await self.emit(endpoint, data, room=target_room, namespace=namespace, callback=cb and srv_callback)
        else:                   # response to sync emit_client_notification
            if cb:
                raise Exception(f"on_call({endpoint}...) - illegal callback argument: {cb}")
            try:
                result = await self.server.call(endpoint, data, to=target_room, namespace=namespace, timeout=timeout)
            except TimeoutError:
                result = None
            return result


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