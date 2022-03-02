import asyncio
import importlib
import inspect
import os
import time

from queue import Empty
from karsalib.struct import CacheQ, FSWatcher
from karsalib.logging import parent_func_name
from socketio import AsyncClientNamespace, AsyncClient
from socketio.exceptions import BadNamespaceError
from multiprocessing import Event, Lock

from .logging import (
                NO_DATA_LOGGING_DEFAULT,
                NO_LOGGING_DEFAULT,
                t_mark
                )
from .util import parse_cmd_args


SERVICE_RESPONSE_TIMEOUT = 10   # response timeout for a sync call to karsa service


def run_streamer_service(StreamerClient,
                         StreamerPublicNamespace,
                         StreamerPrivateNamespace):
    # args: url, port, ns, streamer_type, data_pool_path, data_pool_mask
    args = parse_cmd_args()
    # streamer should always be in private namespace with data producer
    if args['ns'] == '/':
        print( "The service must be in a private namespace.",
               "Please restart the service with --ns option."
              )
        return

    client = None
    while True:
        streamer_type = args.get('streamer_type')
        n_jobs = int(args.get('n_jobs', 1))
        transit = args.get('transit', False)
        # existing target_data_pool_path switches from mode.stream to mode.store
        target_data_pool_path = args.get('target_data_pool_path')
        streamer_opts = {'type': streamer_type,
                         'n_jobs': n_jobs,
                         'transit': transit,
                         'target_data_pool_path': target_data_pool_path
                         }
        data_pool_path = args.get('data_pool_path')
        data_pool_mask = args.get('data_pool_mask')
        data_pool_opts = None if not data_pool_path else \
            {'path': data_pool_path, 'mask': data_pool_mask}
        try:
            client = StreamerClient(streamer_opts,
                                    data_pool_opts,
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
        for s in client.streamers:
            s.shutdown()


class BaseClientNamespace(AsyncClientNamespace):
    """ python-socket.io client namespace for connecting to Router """
    # ref to service client
    parent = None
    # service_state - state vars to report to (re)starting clients
    service_state = {}
    app_name = __file__

    def log(self, *arg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{parent_func_name()}]", *arg)

    async def declare_endpoints(self):
        # endpoints - API providing Router-managed client functionality
        not_endpoints = ['on_connect', 'on_disconnect', 'on_client_notification_callback', ]
        endpoints = [e[3:] for e in dir(self) if e.startswith('on_') and e not in not_endpoints]
        data = dict(
            app_name = self.app_name,
            endpoints = endpoints,
        )
        await self.emit('declare_endpoints', data)
        await self.on_service_state({})
        return endpoints

    async def enter_room(self, room):
        data = dict(
            app_name = self.app_name,
            room = room,
        )
        await self.emit('enter_room', data)

    async def leave_room(self, room):
        data = dict(
            app_name = self.app_name,
            room = room,
        )
        await self.emit('leave_room', data)

    async def on_connect(self):
        self.app_name = self.__class__.__name__
        self.log(f"connected to {self.namespace}")
        # (re)register all private namespaces after root ns is connected
        if self.namespace == '/':
            nss = list(self.parent.sio.namespace_handlers.keys())
            nss.remove(self.namespace)
            for ns in nss:
                await self.emit('register_namespace', ns)
                self.log(f"namespace {ns} registered")
        await self.enter_room(self.room_sid)
        await self.declare_endpoints()

    def on_disconnect(self):
        self.log(f"disconnected from namespace {self.namespace}")

    async def on_service_state(self, data):
        no_logging = data.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = data.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        for n, d in self.service_state.items():
            name = n
            value = d['value']
            room = d.get('room')
            if no_logging:
                pass
            elif no_data_logging:
                self.log(f"{name}: ... to {room}")
            else:
                self.log(f"{name}: {value} to {room}")
            await self.emit('client_notification',
                            {**data, 'name': name, 'value': value, 'room': room})

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
        if cb_ctx is None:
            fn_cb(*arg, **kwarg)
        else:
            fn_cb(cb_ctx, *arg, **kwarg)

    async def emit_client_notification(self, name, value, **kwarg):
        """
        client_notification is sent to API provider via Router,
        name:  a property/API name;
        value: property/API value/argument;
        other key arguments are optional and forwarded along as such,
        e.g. no_logging/no_data_logging=True - skip logging/data_logging; default: False,
        """
        no_logging = kwarg.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = kwarg.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{name}: ... > {kwarg.get('room', name)}")
        else:
            self.log(f"{name}: {value} > {kwarg.get('room', name)}")
        await self.emit('client_notification',
                        {'name': name, 'value': value, **kwarg},
                        )
        if name in self.service_state:
            self.service_state[name] = {'value': value, 'room': kwarg.get('room')}

    async def call_client_notification(self, name, value, **kwarg):
        """
        send client_notification and wait for a response;
        client_notification is sent to API provider via Router,
        name:  a property/API name;
        value: property/API value/argument;
        other key arguments are optional and forwarded along as such,
        e.g. no_logging/no_data_logging=True - skip logging/data_logging; default: False,
        """
        no_logging = kwarg.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = kwarg.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{name}: ... > {kwarg.get('room', name)}")
        else:
            self.log(f"{name}: {value} > {kwarg.get('room', name)}")
        result = await self.client.call('client_notification',
                            {'name': name, 'value': value, **kwarg},
                            timeout=kwarg.get('timeout', SERVICE_RESPONSE_TIMEOUT),
                            )
        if name in self.service_state:
            self.service_state[name] = {'value': value, 'room': kwarg.get('room')}
        return result

    @property
    def room_sid(self):
        return self.parent.sio.get_sid(self.namespace)

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
        # root ns handler is needed to communicate with router at re-connect
        if '/' not in self.sio.namespace_handlers:
            self.sio.register_namespace( BaseClientNamespace('/') )
        for ns_handler in self.sio.namespace_handlers.values():
            ns_handler.parent = self
        # for shutdown sync with threads
        self.shutdown_event = Event()

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
        try:
            while not self.shutdown_event.is_set():
                await self.sio.sleep(1)
        except KeyboardInterrupt as e:
            self.log(f"{e.__class__.__name__}({str(e)})")
        except Exception as e:
            self.log(f"{e.__class__.__name__}({str(e)})")
        finally:
            self.shutdown_event.set()


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
        # set room_instrument in public namespace by private ns_name
        self.public_ns.room_instrument = ns_name
        # cross-references
        self.public_ns.parent = self
        self.private_ns.parent = self
        # for shutdown sync with threads
        self.shutdown_event = Event()

    async def emit_public_notification(self, name, value, **kwarg):
        await self.public_ns.emit_client_notification(name, value, **kwarg)

    async def emit_private_notification(self, name, value, **kwarg):
        await self.private_ns.emit_client_notification(name, value, **kwarg)


# TODO: Sync TOFStreamerClient with TOFService and maybe BaseStreamerClient
class TOFStreamerClient(BridgeServiceClient):
    def __init__(self, streamer_opts, data_pool,
                 url, port, public_namespace_data, private_namespace_data):
        super().__init__(url, port, public_namespace_data, private_namespace_data)
        streamer_type = streamer_opts['type'] or 'TofDaq'
        priv_ns_name, _ = private_namespace_data
        self.instrument_data = {'name': priv_ns_name,
                                'type': streamer_type,
                               }
        self.acknowledge_acquisition = True
        self.requests = CacheQ('client_room')
        self.request_in_progress = dict()
        self.watcher = None
        self.lock = Lock()

        streamer_info = {
            'H5': {'package': 'karsatof', 'module': '.kgenerator'},
            'Raw': {'package': 'karsaorbi', 'module': '.kogenerator'},
            'TofDaq': {'package': 'karsatof', 'module': '.kgenerator'},
        }
        m = importlib.import_module(streamer_info[streamer_type]['module'],
                                    streamer_info[streamer_type]['package'])
        self.streamer = getattr(m, f'{streamer_type}Streamer')(client=self)

        self.data_pool = None
        if data_pool:
            m = importlib.import_module('.datapool', 'karsalib')
            self.data_pool = getattr(m, f'{streamer_type}Pool')(pool_attrs=data_pool)
            self.watcher = FSWatcher(client=self, target_attrs=data_pool, recursive=True)

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
                                    room='room_data_sources',
                                    no_data_logging=False
                                    )


    async def service_main(self):
        self.log('started')
        if self.watcher:
            self.watcher.run_as_daemon()

        # Main loop
        while not self.shutdown_event.is_set():
            # Catch Ctrl+C
            try:
                # Check for active acquisition
                if not self.streamer.active.wait(timeout=.1):
                    await self.sio.sleep(0)
                    # Not yet
                    continue
            except KeyboardInterrupt:
                # Exit
                self.log('KeyboardInterrupt')
                self.shutdown_event.set()
                continue

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
                    self.shutdown_event.set()
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
                                            # cnt=cnt,
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
        self.log('stopped')


class BaseStreamerClient(BridgeServiceClient):
    def __init__(self, streamer_opts, data_pool_opts,
                 url, port, public_namespace_data, private_namespace_data):
        super().__init__(url, port, public_namespace_data, private_namespace_data)
        streamer_type = streamer_opts['type']
        self.n_jobs = streamer_opts['n_jobs']
        self.transit = streamer_opts['transit']
        # target_data_pool_path switches bw stream/store modes
        self.target_data_pool_path = streamer_opts['target_data_pool_path']
        self.streamers = []
        priv_ns_name, _ = private_namespace_data
        self.instrument_data = {'name': priv_ns_name,
                                'type': streamer_type,
                               }
        self.requests = CacheQ('client_room')
        self.in_progress = dict()
        self.responses = CacheQ('client_room/filename')
        self.watcher = None
        self.lock = Lock()

        streamer_info = {
            'H5': {'package': 'karsatof', 'module': '.kgenerator'},
            'Raw': {'package': 'karsaorbi', 'module': '.kogenerator'},
            'TofDaq': {'package': 'karsatof', 'module': '.kgenerator'},
        }
        m = importlib.import_module(streamer_info[streamer_type]['module'],
                                    streamer_info[streamer_type]['package'])
        for _ in range(self.n_jobs):
            self.streamers.append( getattr(m, f'{streamer_type}Streamer')(client=self) )

        self.data_pool = None
        if data_pool_opts:
            m = importlib.import_module('.datapool', 'karsalib')
            self.data_pool = getattr(m, f'{streamer_type}Pool')(pool_attrs=data_pool_opts)
            self.watcher = FSWatcher(client=self, target_attrs=data_pool_opts, recursive=True)

    @property
    def instrument_name(self):
        return self.instrument_data.get('name')

    def is_sample_in_progress(self, filename):
        with self.lock:
            for s in self.streamers:
                if s.filename == filename:
                    return True
        return False

    async def initialize_streamers(self):
        """
        Instantuate streamer instance.
        Should be called from within overridden init_service.
        """
        while True:
            try:
                for i, s in enumerate(self.streamers):
                    s.run_as_daemon()
                    self.log(f'{s.__class__.__name__}: {i+1}/{len(self.streamers)}')
                break
            except Exception as e:
                self.log(f'{e}\nRetrying...')
                await self.sio.sleep(2)
                continue


    async def init_service(self):
        while True:
            # TODO: TBR python-socketio BadNamespaceError connection bug
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
        await self.initialize_streamers()
        await self.emit_private_notification(
                                    'instrument_status',
                                    'ready',
                                    no_data_logging=False,
                                    )
        await self.emit_public_notification(
                                    'instrument_data',
                                    self.instrument_data,
                                    room='room_data_sources',
                                    no_data_logging=False
                                    )


    async def service_main(self):
        self.log('started')
        if self.watcher:
            self.watcher.run_as_daemon()

        while not self.shutdown_event.is_set():
            try:
                data = self.responses.cache_get()
                if not data:
                    await asyncio.sleep(.5)
                    continue
            except KeyboardInterrupt:
                self.log('KeyboardInterrupt')
                break
            except Exception as e:
                self.log(str(e))
                break

            await self.emit_private_notification(
                data['name'],
                data['value'],
                **data['context'],
            )
        self.shutdown_event.set()
        self.log('stopped')
