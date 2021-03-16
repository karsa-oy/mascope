import sys
import getopt
import asyncio
import inspect
from copy import deepcopy
import random
from socketio import AsyncClientNamespace, AsyncNamespace, AsyncClient
from socketio.exceptions import BadNamespaceError

NO_LOGGING_DEFAULT = False
NO_DATA_LOGGING_DEFAULT = True


def copy_dict(d, ignore_keys=[]):
    return {k: v for k, v in d.items() if k not in ignore_keys}

def get_client_notification_args(data):
    """
    Get shallow copy of client_notificaiton arguments
    ignoring 'name' and 'value' fields.
    """
    return copy_dict(data, ignore_keys=['name', 'value'])


class BaseClientNamespace(AsyncClientNamespace):
    """ python-socket.io client namespace for connecting to Router """
    # endpoints - list of notifications the client wants to receive from socket server
    endpoints = []
    # service_state - state vars to report to (re)starting subscribers
    service_state = {}
    app_name = __file__

    def log(self, *arg, **kwarg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    async def subscribe(self, endpoints=None, room=None):
        data = dict(
            app_name = self.app_name,
            endpoints = endpoints or self.endpoints,
            room = room,
        )
        await self.emit('subscribe', data)
        await self.on_service_state(dict(value={},
                                         room=room,
                                         no_data_logging=NO_DATA_LOGGING_DEFAULT, ))

    async def unsubscribe(self, endpoints=None, room=None):
        data = dict(
            app_name = self.app_name,
            endpoints = endpoints or self.endpoints,
            room = room,
        )
        await self.emit('unsubscribe', data)

    async def on_connect(self):
        self.app_name = self.__class__.__name__
        self.log(f"connected to namespace {self.namespace}")
        await self.subscribe()

    def on_disconnect(self):
        self.log(f"disconnected from namespace {self.namespace}")

    async def on_service_state(self, data):
        no_logging = data.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = data.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        for k, v in self.service_state.items():
            if no_logging:
                pass
            elif no_data_logging:
                self.log(f"{k}: ...")
            else:
                self.log(f"{k}: {v}")
            await self.emit('client_notification',
                            {**data, 'name': k, 'value': v})

    def on_client_notification_callback(self, data):
        endpoint = data['endpoint']
        cb_name = data['cb_name']
        cb_ctx = data['cb_ctx']
        arg = data['arg']
        kwarg = data['kwarg']
        no_logging = data.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = data.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{endpoint} callback: ...")
        else:
            self.log(f"{endpoint} callback: {cb_name}(*{arg}, **{kwarg})")
        fn_cb = self.__getattribute__(cb_name)
        if cb_ctx:
            fn_cb(cb_ctx, *arg, **kwarg)
        else:
            fn_cb(*arg, **kwarg)

    async def emit_client_notification(self, name, value, **kwarg):
        """
        client_notification is sent to subscribers via Router,
        name:  a property name;
        value: property value;
        other key arguments are optional and forwarded to subscriber as such,
        e.g. no_logging/no_data_logging=True - skip logging/data_logging; default: False,
        """
        no_logging = kwarg.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = kwarg.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{name}: ...")
        else:
            self.log(f"{name}: {value} > {kwarg.get('room', name)}")
        await self.emit('client_notification', {'name': name, 'value': value, **kwarg})
        if name in self.service_state:
            self.service_state[name] = value


class BaseServerNamespace(AsyncNamespace):
    """ socketio server base namespace class """

    def log(self, *arg, **kwarg):
        print(f"[{self.namespace}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def on_connect(self, sid, environ):
        self.log("connected to namespace", self.namespace)

    async def on_disconnect(self, sid):
        self.log(sid, "disconnected from namespace", self.namespace)
        # clear the app caches, if any, in all app services
        # TODO: move stop_visualize_range to affected services
        await self.on_client_notification(sid,
                        dict(name='stop_visualize_range',
                             value={},
                             no_data_logging=False) )
        # let affected rooms know the client is gone
        for r in self.rooms(sid):
            await self.emit('room_mate_gone', {}, room=r)

    def on_subscribe(self, sid, data):
        """
        Initialize client subscriptions. Subscriptions contain notif names
        the client subscribes for and a room to subscribe into.
        data: dict(app_name=client_name, endpoints, room)
        """
        app_name = data['app_name']
        endpoints = data['endpoints']
        room = data.get('room')
        self.log(f"{app_name}:{room or sid} created endpoints {endpoints}")
        if room:
            self.enter_room(sid, room)
        else:
            for e in endpoints:
                self.enter_room(sid, e)

    async def on_unsubscribe(self, sid, data):
        app_name = data['app_name']
        endpoints = data['endpoints']
        room = data.get('room')
        self.log(f"{app_name}:{room} destroyed endpoints {endpoints}")
        if room:
            self.leave_room(sid, room)
            await self.emit('service_state', {}, room=room)
        else:
            for e in endpoints:
                self.leave_room(sid, e)


    async def on_client_notification(self, sid, data):
        """
        client_notifications on corresponding API endpoints are forwarded by Router from providers
        to subscribers via corresponding endpoints, where name = endpoint is a property name.
        data: dict(name=endpoint_name, value=endpoint_value, ...)
              other named args are free form, e.g. 
              room, cookies, no_logging, no_data_logging...
        """
        no_logging = data.get('no_logging', False)
        no_data_logging = data.get('no_data_logging', True)
        endpoint = data['name']
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
        cookies = data['cookies']
        src_sids = cookies['src_sid']
        # sids are added to the cookies only by this procedure
        src_sids.append(sid)

        target_room = room if room else endpoint

        async def srv_callback(*arg, **kwarg):
            await self.emit('client_notification_callback',
                            dict(endpoint=endpoint,
                                 cb_name=cb, cb_ctx=cb_ctx,
                                 arg=arg, kwarg=kwarg,
                                 **{**get_client_notification_args(data), 'no_logging': True}),
                            room=sid,
                            namespace=self.namespace
                            )
        sent_to = len(src_sids) * '>'
        self.log(f"{endpoint} {sent_to} {namespace}:{target_room}")
        await self.emit(endpoint, data, room=target_room, namespace=namespace, callback=cb and srv_callback)


def parse_cmd_args():
    """
    Parse command line arguments for the service application:
    ------------------------------
    --url : string
        Karsa Router url/ip  (default: localhost)
    --port : int
        Karsa Router port (default: 5010)
    """
    # Set defaults
    url = 'localhost'
    port = 5010
    namespace = '/'
    # Parse cmd arguments
    opts, _ = getopt.getopt(sys.argv[1:], 'o:v', ['url=', 'port=', 'ns='])
    for opt, arg in opts:
        if opt=='--url':
            url = arg
        if opt=='--ns':
            namespace = arg
        if opt=='--port':
            try:
                port = int(arg)
            except:
                raise SyntaxError(f'Invalid command line argument: {opt}={arg}')
    return url, port, namespace


class BaseServiceClient:

    def log(self, *arg, **kwarg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def __init__(self, url, port, client_namespace_data):
        self.addr = f'{url}:{port}'
        if not self.addr.startswith('http'):
            self.addr = 'http://' + self.addr
        self.sio = AsyncClient()
        ns_name, ns_class = client_namespace_data
        if not ns_name.startswith('/'):
            ns_name = '/' + ns_name
        self.sio.register_namespace( ns_class(ns_name) )
        self.ns_handler = self.sio.namespace_handlers.get(ns_name)

    async def emit_client_notification(self, name, value, **kwarg):
        await self.ns_handler.emit_client_notification(name, value, **kwarg)

    async def register_private_namespace_on_router(self, ns_handler):
        self.log(f"Registering {ns_handler.namespace} on Router...")
        await self.sio.connect(self.addr, namespaces=['/',])
        # TODO: TBR python-socketio BadNamespaceError connection bug
        while True:
            try:
                await self.sio.emit('register_namespace',
                                    ns_handler.namespace,
                                    callback=self.disconnect
                                    )
                self.log(f"Registered {ns_handler.namespace}")
                break
            except BadNamespaceError as e:
                self.log(f"Failed: {e}.\nRetrying...")
                await self.sio.sleep(.1)

    async def connect(self, namespaces=None):
        while True:
            try:
                self.log('Connecting to Router...')
                await self.sio.connect(
                            self.addr,
                            namespaces=namespaces
                            )
                self.log("Connected!")
                break
            except Exception as e:
                self.log(f"Failed: {e}\nRetrying...")
                await self.sio.sleep(1)

    async def disconnect(self):
        await self.sio.disconnect()

    async def init_service(self):
        """
        Overridable initialization function of the service
        """
        await self.sio.sleep(0.01)

    async def service_main(self):
        """
        Overridable main function of the service
        """
        while True:
            await self.sio.sleep(1)

    async def run(self):
        if self.ns_handler.namespace != '/':
            await self.register_private_namespace_on_router(self.ns_handler)
        await self.connect([self.ns_handler.namespace])
        await self.init_service()
        await self.service_main()


class BridgeServiceClient(BaseServiceClient):

    def __init__(self, url, port, public_namespace_data, private_namespace_data):
        self.addr = f'{url}:{port}'
        if not self.addr.startswith('http'):
            self.addr = 'http://' + self.addr
        self.sio = AsyncClient()
        # public namespace
        ns_name, ns_class = public_namespace_data
        if ns_name != '/':
            raise BadNamespaceError(f'Invalid root namespace {ns_name}')
        self.sio.register_namespace( ns_class(ns_name) )
        self.public_ns = self.sio.namespace_handlers.get(ns_name)
        # private namespace
        ns_name, ns_class = private_namespace_data
        if not ns_name.startswith('/'):
            ns_name = '/' + ns_name
        self.sio.register_namespace( ns_class(ns_name) )
        self.private_ns = self.sio.namespace_handlers.get(ns_name)
        # cross-references
        self.public_ns.parent = self
        self.private_ns.parent = self

    async def emit_public_notification(self, name, value, **kwarg):
        await self.public_ns.emit_client_notification(name, value, **kwarg)

    async def emit_private_notification(self, name, value, **kwarg):
        await self.private_ns.emit_client_notification(name, value, **kwarg)

    async def run(self):
        await self.register_private_namespace_on_router(self.private_ns)
        await self.connect()
        await self.init_service()
        await self.service_main()
