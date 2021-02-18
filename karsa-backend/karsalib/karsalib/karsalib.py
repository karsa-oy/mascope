import sys
import getopt
import asyncio
import inspect
from copy import deepcopy
import random
from socketio import AsyncClientNamespace, AsyncNamespace, AsyncClient

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
    # rooms - list of notifications the client wants to receive from socket server
    rooms = []
    # service_state - state vars to report to (re)starting subscribers
    service_state = {}
    # app_name is used to detect twin apps
    app_name = __file__
    # type is used to diff service app from client app (python apps are normally services)
    app_type = 'service'

    def log(self, *arg, **kwarg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    async def join_rooms(self):
        data = dict(
            app_name = self.app_name,
            app_type = self.app_type,
            subscriptions = self.rooms,
        )
        await self.emit('subscribe', data)

    async def on_connect(self):
        self.app_name = self.__class__.__name__
        self.log(f"connected to namespace {self.namespace}")
        await self.join_rooms()
        await self.on_service_state(dict(value={},
                                         notify_twin_clients=True,
                                         notify_twin_services=True,
                                         no_data_logging=False, ))

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
        subscription = data['subscription']
        cb_name = data['cb_name']
        cb_ctx = data['cb_ctx']
        arg = data['arg']
        kwarg = data['kwarg']
        no_logging = data.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = data.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{subscription} callback: ...")
        else:
            self.log(f"{subscription} callback: {cb_name}(*{arg}, **{kwarg})")
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
        e.g. no_logging/no_data_logging=True - skip logging/data_logging in Router; default: False,
        """
        no_logging = kwarg.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = kwarg.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{name}: ...")
        else:
            self.log(f"{name}: {value}")
        await self.emit('client_notification', {'name': name, 'value': value, **kwarg})
        if name in self.service_state:
            self.service_state[name] = value


class BaseServerNamespace(AsyncNamespace):
    """ socketio server base namespace class """
    subscription_sids = dict()
    sid_to_app = dict()
    app_name_to_sids = dict()   # for tracing service/app twins

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def add_subscription(self, sid, room):
        if room not in self.subscription_sids:
            self.subscription_sids[room] = []
        if sid not in self.subscription_sids[room]:
            self.subscription_sids[room].append(sid)
        self.enter_room(sid, f'{room}_{sid}')

    def remove_subscription(self, sid, room):
        self.leave_room(sid, f'{room}_{sid}')
        self.subscription_sids[room].remove(sid)
    
    def on_connect(self, sid, environ):
        self.log("connected to namespace", self.namespace)

    async def on_disconnect(self, sid):
        if sid not in self.sid_to_app:
            # don't unsubscribe anonimous clients (UI:renderer?)
            return
        app_name = self.sid_to_app[sid]['name']
        app_type = self.sid_to_app[sid].get('type', 'client')
        self.log(app_type, app_name, "disconnected from namespace", self.namespace)
        # clear the app caches, if any, in all app services
        await self.on_client_notification(sid,
                        dict(name='stop_visualize_range',
                             value={},
                             notify_twin_services=True,
                             no_data_logging=False) )
        # remove the app from all rooms/subscriptions
        for room in self.subscription_sids:
            try:
                self.remove_subscription(sid, room)
            except:
                pass
        del self.sid_to_app[sid]
        # remove the app from twin apps list
        self.app_name_to_sids[app_name].remove(sid)
        if not self.app_name_to_sids[app_name]:
            del self.app_name_to_sids[app_name]


    def on_subscribe(self, sid, data):
        """
        Initialize client subscriptions. 
        Subscriptions contain prop names the client subscribes for.
        data: dict(app_name=client_name, [app_type=client_type,] subscriptions=subscription_list)
        """
        app_name = data['app_name']
        app_type = data.get('app_type', 'client')
        self.log(f"{app_type} {app_name}:{sid} joined rooms {data['subscriptions']}")
        self.sid_to_app[sid] = dict(name=app_name, type=app_type)
        if app_name not in self.app_name_to_sids:
            self.app_name_to_sids[app_name] = []
        self.app_name_to_sids[app_name].append(sid)
        for d in data['subscriptions']:
            self.add_subscription(sid, d)

    def on_unsubscribe(self, sid, data):
        self.log(f"client {data['app_name']} leaved rooms {data['subscriptions']}")
        for d in data['subscriptions']:
            self.remove_subscription(sid, d)


    async def on_client_notification(self, sid, data):
        """
        client_notifications are forwarded by Router from providers
        to subscribers via corresponding rooms, where a room is a property name.
        data: dict(name=prop_name, value=prop_value, no_logging=bool, no_data_logging=bool, ...)
              all key-value pairs in data dict are forwarded to subscriber,
              no_logging/no_data_logging - skip logging/data logging in subscriber; default: False,
        """
        no_logging = data.get('no_logging', False)
        no_data_logging = data.get('no_data_logging', True)
        notify_twin_clients = data.get('notify_twin_clients', False)   # overriding rule, if defined
        notify_twin_services = data.get('notify_twin_services', False)   # overriding rule, if defined
        subscription = data['name']
        cb = data.pop('callback', None)
        cb_ctx = data.pop('callback_context', None)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{subscription}: ...")
        else:
            self.log(data)

        if 'cookies' not in data:
            data['cookies'] = dict(src_sid=[])
        cookies = data['cookies']
        if subscription not in self.subscription_sids:
            self.log(f"{subscription}: no handlers - notification dropped.")
            return
        src_sids = cookies['src_sid']
        # sids are added to the cookies only by this procedure
        src_sids.append(sid)
        # shuffle for naive balance loading in case of twin services
        subscription_sids = deepcopy(self.subscription_sids[subscription])
        # random.shuffle(subscription_sids)
        # # do not forward notification to self and self twins
        # the_twin_app_sids = self.app_name_to_sids[self.sid_to_app[sid]['name']]
        # for s in the_twin_app_sids:
        #     try:
        #         subscription_sids.remove(s)
        #     except:
        #         # self may not be subscribed to this notification: ignore
        #         pass
        # by default, namespace client (both app client, and app service)
        # notifies only one of the subscriber twins (if any); when defined, the flags
        # notify_twin_clients/services alter subscriber notification rule for twins
        # subscription_sids = self.remove_twin_app_sids(sids=subscription_sids,
        #                                             sids_to_stay=src_sids,
        #                                             keep_twin_clients=notify_twin_clients,
        #                                             keep_twin_services=notify_twin_services)
        async def srv_callback(*arg, **kwarg):
            await self.emit('client_notification_callback',
                            dict(subscription=subscription,
                                 cb_name=cb, cb_ctx=cb_ctx,
                                 arg=arg, kwarg=kwarg,
                                 no_logging=True,
                                 **get_client_notification_args(data)),
                            room=sid)

        for target_sid in subscription_sids:
            sent_to = len(src_sids) * '>'
            self.log(f"{subscription}: {self.sid_to_app[sid]['name']} {sent_to} {self.sid_to_app[target_sid]['name']}")
            room = f"{subscription}_{target_sid}"
            await self.emit(subscription, data, room=room, callback=cb and srv_callback)


    def remove_twin_app_sids(self, sids, sids_to_stay,
                             keep_twin_clients=False,
                             keep_twin_services=False):
        """
           Remove socket_ids of twin applications from sids array;
           If sids_to_stay contain the twin app socket_id, then leave
           it in resulting array and remove the twin sid.
        """
        res = []
        # make sure relevant sids_to_stay members get to a result array
        for s in sids_to_stay:
            if s in sids:
                res.append(s)
                if (self.sid_to_app[s]['type'] == 'client' and keep_twin_clients) or \
                   (self.sid_to_app[s]['type'] == 'service' and keep_twin_services) :
                    sids.remove(s)
                else:
                    self.remove_sid_with_twins(sids, s)
        # check the rest of sids array
        while sids:
            s = sids[0]
            res.append(s)
            if (self.sid_to_app[s]['type'] == 'client' and keep_twin_clients) or \
               (self.sid_to_app[s]['type'] == 'service' and keep_twin_services) :
                sids.pop(0)
            else:
                self.remove_sid_with_twins(sids, s)
        return res

    def remove_sid_with_twins(self, sids, sid_to_remove):
        twin_sids_to_remove = self.app_name_to_sids[self.sid_to_app[sid_to_remove]['name']]
        for s in twin_sids_to_remove:
            sids.remove(s)


def parse_cmd_args():
    """
    Parse command line arguments for the service application:
    ------------------------------
    --url : string
        Karsa Router url/ip  (default: localhost)
    --port : int
        Karsa Router port (default: 5010)
    """
    url = 'localhost'
    port = 5010
    opts, _ = getopt.getopt(sys.argv[1:], 'o:v', ['url=', 'port=', ])
    for opt, arg in opts:
        if opt=='--url':
            url = arg
        if opt=='--port':
            try:
                port = int(arg)
            except:
                raise SyntaxError(f'Invalid command line argument: {opt}={arg}')
    return url, port


class BaseServiceClient:

    def log(self, *arg, **kwarg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def __init__(self, url, port, client_namespace):
        self.addr = f'{url}:{port}'
        if not self.addr.startswith('http'):
            self.addr = 'http://' + self.addr
        self.sio = AsyncClient()
        self.namespaces = []
        if not isinstance(client_namespace, list):
            self.sio.register_namespace(client_namespace('/'))
            self.namespaces.append('/')
        else:
            for namespace, handlers in client_namespace:
                self.sio.register_namespace( handlers(namespace) )
                self.namespaces.append(namespace)
        self.root_ns = self.sio.namespace_handlers.get(self.namespaces[0])

    async def emit_client_notification(self, name, value, **kwarg):
        await self.root_ns.emit_client_notification(name, value, **kwarg)

    async def connect(self):
        while True:
            try:
                self.log('Connecting to Router...')
                await self.sio.connect(self.addr, namespaces=self.namespaces)
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
        await self.connect()
        await self.init_service()
        await self.service_main()
