import sys
import os
import time
import getopt
import asyncio
import inspect
from copy import deepcopy
import random
import logging
from socketio import AsyncClientNamespace, AsyncNamespace, AsyncClient
from socketio.exceptions import BadNamespaceError
from queue import Empty, Full
from threading import Thread
from multiprocessing import Event, Lock, cpu_count


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

def this_func_name():
    return inspect.stack()[1][3]

def parent_func_name():
    return inspect.stack()[2][3]

def t_mark(data, note=None):
    if 't_mark' not in os.environ:
        return
    if 't_mark' not in data:
        data['t_mark'] = [[note or parent_func_name(), time.time()],]
        return
    t = time.time()
    data['t_mark'][-1][-1] = round(t - data['t_mark'][-1][-1], 3)
    data['t_mark'].append([note or parent_func_name(), t])
    print('t_mark :', data['t_mark'], data.get('request_id', data.get('filename', '')))


class LRUDict(dict):
    def __init__(self, capacity: int, *args, **kwargs):
        self.capacity = capacity
        self.lru_keys = []
        self.lock = Lock()
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        with self.lock:
            data = super().__getitem__(key)
            self.lru_keys.remove(key)
            self.lru_keys.append(key)
            return data

    def __setitem__(self, key, value):
        with self.lock:
            super().__setitem__(key, value)
            if key in self.lru_keys:
                self.lru_keys.remove(key)
            self.lru_keys.append(key)
            if len(self.lru_keys) > self.capacity:
                k = self.lru_keys.pop(0)
                super().__delitem__(k)


class Logger():
    # log_levels = [
    #     logging.DEBUG,
    #     logging.INFO,
    #     logging.WARNING,
    #     logging.ERROR,
    #     logging.CRITICAL,
    # ]
    def __init__(self, fname, c_log_level='INFO', f_log_level='DEBUG', mode='r+'):
        # notification sender configuration and
        # methods are borrowed from client class
        self.target_room = None
        self.emit_client_notification = None
        # logger configuration
        self.logger = logging.getLogger(fname)
        self.logger.setLevel('DEBUG')
        # console logger
        if c_log_level:
            c_handler = logging.StreamHandler()
            c_handler.setLevel(level=c_log_level)
            c_format = logging.Formatter('%(message)s')
            c_handler.setFormatter(c_format)
            self.logger.addHandler(c_handler)
        # file logger
        if f_log_level:
            try:
                f_handler = logging.FileHandler(fname + '.log', mode=mode)
                f_handler.setLevel(level=f_log_level)
                f_format = logging.Formatter('%(asctime)s %(message)s')
                f_handler.setFormatter(f_format)
                self.logger.addHandler(f_handler)
            except FileNotFoundError:
                pass

    def configure_notifications(self, sender, target_room):
        if sender:
            self.emit_client_notification = sender.__getattribute__('emit_client_notification')
        if target_room:
            self.target_room = target_room

    def debug(self, m):
        self.logger.debug(m)

    def info(self, m):
        self.logger.info(m)

    def warning(self, m, room=None, namespace='/'):
        self.logger.warning(m)
        if self.emit_client_notification and self.logger.isEnabledFor(logging.WARNING):
            self.emit_client_notification('service_warning', m,
                                      room=room or self.target_room,
                                      namespace=namespace,
                                      no_logging=False,
                                      no_data_logging=False)

    def error(self, m, room=None, namespace='/'):
        self.logger.error(m)
        if self.emit_client_notification and self.logger.isEnabledFor(logging.ERROR):
            self.emit_client_notification('service_error', m,
                                      room=room or self.target_room,
                                      namespace=namespace,
                                      no_logging=False,
                                      no_data_logging=False)

    def critical(self, m, room=None, namespace='/'):
        self.logger.critical(m)
        if self.emit_client_notification and self.logger.isEnabledFor(logging.CRITICAL):
            self.emit_client_notification('service_critical_error', m,
                                      room=room or self.target_room,
                                      namespace=namespace,
                                      no_logging=False,
                                      no_data_logging=False)


class QConnect(Thread):
    OUT_Q_LIMIT = cpu_count()
    CACHE_LIMIT = 1000000   # TODO: number?

    def __init__(self, in_q=None, out_q=None, shutdown_event=None):
        Thread.__init__(self)
        self.in_q = in_q
        self.out_q = out_q
        self.shutdown_event = shutdown_event
        self.input_ready = Event()
        self.input_ready.set()
        self.cache = []

    def put(self, data):
        self.input_ready.wait()
        self.input_ready.clear()
        self.in_q.put(data)
        self.input_ready.wait()

    def get(self, *args, **kwargs):
        return self.out_q.get(*args, **kwargs)

    def cache_put(self, data):
        if len(self.cache) > self.CACHE_LIMIT:
            raise Full
        self.cache.insert(0, data)

    def cache_get(self):
        data = self.cache.pop()
        return data

    def fits_filter(self, data):
        return False

    def run(self):
        while not self.shutdown_event.is_set():
            data = None
            try:
                data = self.in_q.get_nowait()
                # print('in_q.get', data.get('request_id', ':'.join([data.get('name','?'), data.get('key','?')])))
            except Empty:
                pass
            except KeyboardInterrupt:
                self.input_ready.set()
                break
            if data:
                if self.fits_filter(data):
                    continue
                try:
                    self.cache_put(data)
                except Full as e:
                    print("Cache overflow -- skipping input!")
                finally:
                    self.input_ready.set()
            if self.out_q.qsize() >= self.OUT_Q_LIMIT:
                time.sleep(.01)
                continue
            data = self.cache_get()
            if data:
                self.out_q.put(data)
                # print('out_q.put', data.get('request_id', ':'.join([data.get('name','?'), data.get('key','?')])))
            else:
                time.sleep(.01)
        self.cache = None
        print(f"Exit from {self.__class__.__name__} thread")


class CacheQ(QConnect):
    def __init__(self, cache_key, *arg, **kwarg):
        super().__init__(*arg, **kwarg)
        self.cache = dict()
        self.cache_key_separator = kwarg.get('cache_key_separator', '/')
        self.cache_key = cache_key.split(self.cache_key_separator)
        self.cache_index = len(self.cache_key) * [0]
        self.cache_index[0] = -1
        self.lock = Lock()
        self.in_q_filters = []

    def cache_put(self, data):
        keys = []
        for k in self.cache_key:
            keys.append(data.get(k, 'default'))
        cache_depth = len(keys) - 1
        cache_level = self.cache
        with self.lock:
            for i, k in enumerate(keys):
                if k not in cache_level:
                    cache_level[k] = [] if i == cache_depth else {}
                cache_level = cache_level[k]
            cache_level.insert(0, data)

    def _inc_cache_level_index(self, dic, index):
        step = min(len(dic), index + 1)
        next_index = step % len(dic)
        index_shift = step // len(dic)
        return next_index, index_shift

    def _inc_cache_index(self):
        cache_level = self.cache
        for i in range(len(self.cache_index)):
            self.cache_index[i], shift = self._inc_cache_level_index(cache_level, self.cache_index[i])
            if not shift:
                break
            next_key = list(cache_level.keys())[self.cache_index[i]]
            cache_level = cache_level[next_key]

    def cache_get(self):
        self.lock.acquire()
        cache_level_keys = []
        cache_level_dics = []
        cache_level = self.cache
        cache_level_dics.append(cache_level)
        try:
            self._inc_cache_index()
        except:
            self.lock.release()
            return None
        for i in self.cache_index:
            try:
                key = list(cache_level.keys())[i]
            except IndexError:
                self.lock.release()
                return self.cache_get()
            cache_level = cache_level[key]
            cache_level_dics.append(cache_level)
            cache_level_keys.append(key)
        data = cache_level.pop()
        if not cache_level:             # no more data in this cache element - clean up
            for d, k in reversed(list(zip(cache_level_dics, cache_level_keys))):
                if not d[k]:
                    del d[k]
        self.lock.release()
        return data

    def cache_delete_key(self, key):
        with self.lock:
            if self.in_q:
                # set ignore-marker for data, which is pending in in_q
                self.in_q_filters.append(key)
                self.in_q.put({'name': '__stop_fits_filter', 'key': key})
            # delete cache hierarchy for the key
            level_keys = key.split(self.cache_key_separator)
            cache_level = self.cache
            key_to_delete = level_keys.pop(0)
            while level_keys:
                cache_level = cache_level[key_to_delete]
                key_to_delete = level_keys.pop(0)
            if key_to_delete in cache_level:
                del cache_level[key_to_delete]

    def fits_filter(self, data):
        with self.lock:
            # filter out ignore-marker package
            if data.get('name') == '__stop_fits_filter':
                # print('__stop_fits_filter', data['key'])
                self.in_q_filters.remove(data['key'])
                return True
            # check if input data fits any filter element
            for filter in self.in_q_filters:
                fit = True
                for k, v in zip(self.cache_key, filter.split(self.cache_key_separator)):
                    if data.get(k) != v:
                        fit = False
                        break
                if fit:
                    # print('fits_filter', filter)
                    return True
            return False

    def cache_size(self, cache_level=None):
        cache_level = cache_level or self.cache
        if isinstance(cache_level, list):
            return len(cache_level)
        return sum([self.cache_size(v) for v in cache_level.values()])

class BaseClientNamespace(AsyncClientNamespace):
    """ python-socket.io client namespace for connecting to Router """
    # ref to service client
    parent = None
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
        self.log(f"connected to {self.namespace}")
        await self.subscribe()
        # (re)register all private namespaces after root ns is connected
        if self.namespace == '/':
            nss = list(self.client.namespace_handlers.keys())
            nss.remove(self.namespace)
            for ns in nss:
                await self.emit('register_namespace', ns)
                self.log(f"namespace {ns} registered")

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
        await self.emit('client_notification',
                        {'name': name, 'value': value, **kwarg},
                        )
        if name in self.service_state:
            self.service_state[name] = value

    @property
    def room_sid(self):
        return self.parent.sio.get_sid(self.namespace)

class BaseServerNamespace(AsyncNamespace):
    """ socketio server base namespace class """

    def log(self, *arg, **kwarg):
        print(f"[{self.namespace}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def on_connect(self, sid, environ):
        self.log("connected to namespace", self.namespace)

    async def on_disconnect(self, sid):
        self.log(sid, "disconnected from namespace", self.namespace)
        # clear the app caches, if any, in all app services
        # TODO:
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
        if room:
            self.log(f"{app_name}:{sid} joins room {room}")
            self.enter_room(sid, room)
        else:
            self.log(f"{app_name}:{sid} joins rooms {endpoints}")
            for e in endpoints:
                self.enter_room(sid, e)
        self.log(f"{app_name}:{sid} stays in rooms: {self.rooms(sid)}")

    async def on_unsubscribe(self, sid, data):
        app_name = data['app_name']
        endpoints = data['endpoints']
        room = data.get('room')
        if room:
            self.log(f"{app_name}:{sid} leaves room {room}")
            self.leave_room(sid, room)
            await self.emit('service_state', {}, room=room)
        else:
            self.log(f"{app_name}:{sid} leaves rooms {endpoints}")
            for e in endpoints:
                self.leave_room(sid, e)
        self.log(f"{app_name}:{sid} stays in rooms: {self.rooms(sid)}")


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
    args_cmd = dict()
    args_file = dict()
    args_default = dict(url='localhost', port=5010, ns='/')
    # Parse cmd arguments
    opts, _ = getopt.getopt(sys.argv[1:], 'o:v',
                ['config=',
                 'n_jobs=',
                 'ns=',
                 'port=',
                 'raw_pool=',
                 'streamer_type=',
                 'url=',
                 ])
    for opt, arg in opts:
        assert opt[:2]=='--', f"Invalid argument {opt}"
        key = opt[2:]
        if key.lower() == 'config':
            # service config may be defined in yaml file
            import yaml
            with open(arg, 'r') as f:
                args_file = yaml.safe_load(f)
            continue
        args_cmd[key] = arg
    # command line options override the ones from the config file
    return {**args_default, **args_file, **args_cmd}


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
        self.log('Register handler for namespace', ns_name)
        self.sio.register_namespace( ns_class(ns_name) )
        self.ns_handler = self.sio.namespace_handlers.get(ns_name)
        self.ns_handler.parent = self
        # root ns handler is needed to communicate with router at re-connect
        if '/' not in self.sio.namespace_handlers:
            self.sio.register_namespace( BaseClientNamespace('/') )

    async def emit_client_notification(self, name, value, **kwarg):
        await self.ns_handler.emit_client_notification(name, value, **kwarg)

    async def connect(self, namespaces=None):
        self.log('Connecting to Router...')
        while True:
            try:
                await self.sio.connect(
                            self.addr,
                            namespaces=namespaces
                            )
                self.log("Connected to Router")
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
        self.log('Register handler for namespace', ns_name)
        self.sio.register_namespace( ns_class(ns_name) )
        self.public_ns = self.sio.namespace_handlers.get(ns_name)
        # private namespace
        ns_name, ns_class = private_namespace_data
        if not ns_name.startswith('/'):
            ns_name = '/' + ns_name
        self.log('Register handler for namespace', ns_name)
        self.sio.register_namespace( ns_class(ns_name) )
        self.private_ns = self.sio.namespace_handlers.get(ns_name)
        # cross-references
        self.public_ns.parent = self
        self.private_ns.parent = self

    async def emit_public_notification(self, name, value, **kwarg):
        await self.public_ns.emit_client_notification(name, value, **kwarg)

    async def emit_private_notification(self, name, value, **kwarg):
        await self.private_ns.emit_client_notification(name, value, **kwarg)
    
    

class BaseStreamerClient(BridgeServiceClient):
    def __init__(self, streamer_type, raw_pool,
                 url, port, public_namespace_data, private_namespace_data):
        # Caller must have corresponding streamer and pool classes imported
        try:
            streamer_class = inspect.stack()[1][0].f_globals[f"{streamer_type}Streamer"]
        except KeyError:
            s = f"Invalid streamer_type : {streamer_type}" if streamer_type else \
                f"Missing streamer_type argument"
            raise Exception(s)
        self.streamer = streamer_class()
        self.raw_pool = None
        self.raw_pool_path = raw_pool
        if raw_pool:
            raw_pool_class = inspect.stack()[1][0].f_globals[f"{streamer_type}Pool"]
            self.raw_pool = raw_pool_class(raw_pool)
        super().__init__(url, port, public_namespace_data, private_namespace_data)
        priv_ns_name, _ = private_namespace_data
        self.instrument_data = {'name': priv_ns_name,
                                'type': streamer_type,
                               }
        self.public_ns.room_instrument = priv_ns_name
        self.acknowledge_acquisition = True

    @property
    def instrument_name(self):
        return self.instrument_data.get('name')

    async def initialize_streamer(self):
        """
        Instantuate streamer instance.
        Should be called from within overridden init_service.
        """
        while True:
            try:
                self.streamer.start()
                break
            except Exception as e:
                self.log(f'{e}\nRetrying...')
                await self.sio.sleep(2)
                continue


    async def init_service(self):
        while True:
            # TODO: TBR python-socketio BadNamespaceError connection bug
            from socketio.exceptions import BadNamespaceError
            try:
                await self.emit_private_notification(
                                            'instrument_status',
                                            'not_ready',
                                            no_data_logging=False
                                            )
                break
            except BadNamespaceError:
                await self.sio.sleep(.1)
                continue
        await self.initialize_streamer()
        await self.emit_private_notification(
                                    'instrument_status',
                                    'ready',
                                    no_data_logging=False,
                                    )
        await self.emit_public_notification(
                                    'instrument_data',
                                    self.instrument_data,
                                    room=self.public_ns.room_data_sources,
                                    no_data_logging=False
                                    )


    async def service_main(self):
        # Main loop
        while True:
            # Catch Ctrl+C
            try:
                # Check for active acquisition
                if not self.streamer.active.wait(timeout=.1):
                    await self.sio.sleep(0)
                    # Not yet
                    continue
            except KeyboardInterrupt:
                # Exit
                break

            # Initialize acquisition
            self.log("Initializing acquisition.")
            await self.emit_private_notification(
                                        'acquisition_status',
                                        'running',
                                        )

            filename_base = self.streamer.filename
            # Prepend with instrument name
            filename = '_'.join([self.instrument_name,
                                 filename_base
                                 ])
            # Replace spaces with underscore
            filename = filename.replace(' ', '_')

            t_data = {'filename': filename}
            t_mark(t_data, 'acquisition_start')

            await self.emit_private_notification(
                                        'acquisition_coordinates',
                                        {'filename': filename,
                                         'mz': self.streamer.mz.tobytes(),
                                         't_range': [0, self.streamer.length]
                                         },
                                        no_data_logging=True
                                        )
            await self.emit_public_notification(
                                        'acquisition_coordinates',
                                        {'filename': filename,
                                         'mz': self.streamer.mz.tobytes(),
                                         't_range': [0, self.streamer.length]
                                         },
                                        no_data_logging=True
                                        )
            if hasattr(self.streamer, 'tps_info'):
                await self.emit_private_notification(
                                            'tps_parameter_info',
                                            {'filename': filename,
                                             'tps_info': self.streamer.tps_info,
                                             },
                                            )
            await self.emit_private_notification(
                                        'acquisition_started',
                                        {'filename': filename,
                                         'mz_range': [float(self.streamer.mz[0]), float(self.streamer.mz[-1])],
                                         't_range': [0, self.streamer.length],
                                        },
                                       )
            # Acquisition loop
            self.log("Entering acquisition loop.")
            MAX_RESPONSE_TIME = 15      # secs to wait for client acknowledgement, then ignore it.

            # # inject callback handler to private_ns to handle emit result in the notification namespace
            # def private_ns_data_count(cnt):
            #     self.private_ns.cnt = max(cnt, self.private_ns.cnt)
            #     self.private_ns.cnt_timestamp = time.time()

            # self.private_ns.private_ns_data_count = private_ns_data_count
            # self.private_ns.cnt = 0
            # self.private_ns.cnt_timestamp = time.time()
            # cnt = 0

            # inject callback handler to public_ns to handle emit result in the notification namespace
            def public_ns_data_count(cnt):
                self.public_ns.cnt = max(cnt, self.public_ns.cnt)
                self.public_ns.cnt_timestamp = time.time()

            self.public_ns.public_ns_data_count = public_ns_data_count
            self.public_ns.cnt = 0
            self.public_ns.cnt_timestamp = time.time()
            cnt = 0


            while True:
                try:
                    spec_data = self.streamer.spec_queue.get_nowait() # Non-blocking
                    # acquisition ACK: sync acquisition velocity with FileIo capacity
                    # while cnt - self.private_ns.cnt > 4:
                    #     if time.time() - self.private_ns.cnt_timestamp > MAX_RESPONSE_TIME:
                    #         self.log(f"Warning: no acknowledgement for packets {self.private_ns.cnt}-{cnt} of {filename}")
                    #         private_ns_data_count(cnt)
                    #         raise ConnectionError
                    #     await self.sio.sleep(.1)

                    # acquisition ACK: sync acquisition velocity with DataViz capacity
                    # TODO: tmp solution: use public_ns cnt, since it goes to DataViz and is slower than private_ns.cnt for FileIO
                    while cnt - self.public_ns.cnt > 4:
                        if time.time() - self.public_ns.cnt_timestamp > MAX_RESPONSE_TIME:
                            self.log(f"Warning: no acknowledgement for packets {self.public_ns.cnt}-{cnt} of {filename}")
                            public_ns_data_count(cnt)
                            raise ConnectionError
                        await self.sio.sleep(.1)

                    if hasattr(self.streamer, 'tps_queue'):
                        tps_data = self.streamer.tps_queue.get() # Blocking, since new data expected
                    else:
                        tps_data = None
                except Empty:
                    # No new data
                    await self.sio.sleep(.1)
                    continue
                except ConnectionError:
                    self.streamer.stop_stream()
                    self.log(f"Acquisition of {filename} was stopped.")
                    continue
                except KeyboardInterrupt:
                    self.streamer.shutdown()
                    spec_data = None
                    self.log(f"Acquisition of {filename} was cancelled.")
                    break

                # Got data
                if spec_data is not None:
                    # Spectrum data
                    if self.acknowledge_acquisition:
                        cnt += 1
                    await self.emit_private_notification(
                                            'acquired_spectrum',
                                            {**spec_data,
                                             'filename': filename
                                             },
                                            # callback="private_ns_data_count",
                                            cnt=cnt,
                                            no_data_logging=True
                                            )
                    await self.emit_public_notification(
                                            'acquired_spectrum',
                                            {**spec_data,
                                             'filename': filename
                                             },
                                            callback="public_ns_data_count",
                                            cnt=cnt,
                                            no_data_logging=True
                                            )
                    # Progress
                    await self.emit_private_notification(
                                            'acquisition_progress',
                                            {'progress': self.streamer.progress,
                                             },
                                            no_data_logging=False
                                            )
                    if tps_data:
                        # TPS data
                        await self.emit_private_notification(
                                                'acquired_tps_data',
                                                {**tps_data,
                                                 'filename': filename
                                                 },
                                                no_data_logging=True
                                                )
                # Got poison pill
                else:
                    # Finalize acquisition
                    await self.emit_private_notification(
                                            'acquisition_progress',
                                            {'progress': 100.,
                                             },
                                            no_data_logging=False
                                            )
                    await self.emit_private_notification(
                                            'acquisition_finished',
                                            {'filename': filename
                                             },
                                            )
                    await self.emit_public_notification(
                                            'acquisition_finished',
                                            {'filename': filename
                                             },
                                            )
                    await self.emit_private_notification(
                                            'acquisition_status',
                                            'not_running',
                                            )
                    t_mark(t_data, 'acquisition_done')
                    self.log("Exiting acquisition loop.")
                    break # Break out of acquisition loop
        # Out of main loop
        # Kill Acquisition
        self.streamer.shutdown()



def run_streamer_service(StreamerClient,
                         StreamerPublicNamespace,
                         StreamerPrivateNamespace):
    # args: url, port, ns, streamer_type, raw_pool
    args = parse_cmd_args()
    # streamer should always be in private namespace with data producer
    if args['ns'] == '/':
        print( "The service must be in a private namespace.",
               "Please restart the service with --ns option."
              )
        return

    client = None
    while True:
        try:
            client = StreamerClient(args.get('streamer_type', None),
                                    args.get('raw_pool', None),
                                    args['url'],
                                    args['port'],
                                    ('/', StreamerPublicNamespace),
                                    (args['ns'], StreamerPrivateNamespace)
                                )
            break
        except ModuleNotFoundError as e:
            print(str(e))
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                print('Cancelled')
                return
        except:
            raise

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        client.streamer.shutdown()
