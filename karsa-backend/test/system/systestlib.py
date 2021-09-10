#!/bin/pyton3

import os
import time
import asyncio
from decorator import decorator

from multiprocessing import Event
from threading import Timer, Thread

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import parse_cmd_args

# service_q = None

# samples table contains declarative criteria for successfull request
# TODO: read the data from attr file
samples = {'TofDaq_Data_2021.08.02_01h01m01s': {'t_range_max': 30, 'max_exec_time': 10}}


def get_namespace(filename):
    return '/' + filename.split('_')[0]

# TODO: tmp fix - https://github.com/aio-libs/aiohttp/issues/4324
from asyncio.proactor_events import _ProactorBasePipeTransport
@decorator
def bug_workaround(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except RuntimeError as e:
        if str(e) != 'Event loop is closed':
                raise
_ProactorBasePipeTransport.__del__ = bug_workaround(_ProactorBasePipeTransport.__del__)


class BaseTestClientNamespace(BaseClientNamespace):
    endpoints = [
        'projects',
        'project_selected',
        'experiments',
        'experiment_selected',
        'samples',
        'save_experiment',
        'delete_experiment',
        'delete_project',
        ]
    endpoints_room_sid = [
        # 'loaded_coordinates',   # response to coordinate_request
        'figure_data',
        ]
    endpoints_room_instrument = []

    async def subscribe(self):
        if self.endpoints:
            await super().subscribe(self.endpoints)
        if self.endpoints_room_sid:
            await super().subscribe(self.endpoints_room_sid, self.room_sid)
        if self.endpoints_room_instrument:
            await super().subscribe(self.endpoints_room_instrument, self.room_instrument)


    # helpers

    def check_figure_data_request_finished(self, data):
        request_id = data['value']['request_id']
        t_range_1 = data['value']['t_range'][1]
        r_type, t_start, t_range_max, max_exec_time = request_id.split('_')
        done = int(t_range_max) <= int(t_range_1)
        if done:
            self.parent.kill_exec_timer(request_id)
            self.parent.mark_request_done(request_id)


    # test validators
    
    # # TODO: smth wrong with this notificaiton: we just need ranges, but it gives huge coords array
    # async def on_loaded_coordinates(self, data):
    #     self.log(data['value']['request_id'])
    #     self.log(data['value']['data_type'])
    #     self.log(data['value']['dims'])     #
    #     # self.log(data['value']['coordinates'])  -  why so long???
    #     # service_q.cache_put(data)


    async def on_figure_data(self, data):
        self.log({k:data['value'].get(k, 'missing') for k in ['request_id', 'viz_type', 't_range', 'mz_range']})
        # service_q.cache_put(data)
        self.check_figure_data_request_finished(data)

    async def on_projects(self, data):
        self.parent.projects = {d['title']:d for d in data['value']}
        self.parent.projects_root = os.path.dirname(data['value'][0]['path'])
        self.log(self.parent.projects_root, list(self.parent.projects.keys()))
        request_id = data['request_id']
        self.parent.kill_exec_timer(request_id)
        self.parent.mark_request_done(request_id)

    async def on_project_selected(self, data):
        self.log(data['value']['title'])

    async def on_experiments(self, data):
        # project_selected emits experiments
        for e in data['value']:
            if 'experiments' not in self.parent.projects[e['project']]:
                self.parent.projects[e['project']]['experiments'] = {}
            self.parent.projects[e['project']]['experiments'][e['title']] = e
        p_sel = data['value'][0]['project']
        self.log(p_sel, list(self.parent.projects[p_sel]['experiments'].keys()))
        request_id = data['request_id']
        self.parent.kill_exec_timer(request_id)
        self.parent.mark_request_done(request_id)

    async def on_experiment_selected(self, data):
        self.log(data['value']['project'], data['value']['title'])

    async def on_samples(self, data):
        # experiment_selected emits samples
        for n, s in data['value'].items():
            if 'samples' not in self.parent.projects[s['project']]['experiments'][s['experiment']]:
                self.parent.projects[s['project']]['experiments'][s['experiment']]['samples'] = {}
            self.parent.projects[s['project']]['experiments'][s['experiment']]['samples'][n] = s
            p_sel = s['project']
            e_sel = s['experiment']
        self.log(p_sel, list(self.parent.projects[p_sel]['experiments'][e_sel].keys()))
        request_id = data['request_id']
        self.parent.kill_exec_timer(request_id)
        self.parent.mark_request_done(request_id)

    async def on_save_experiment(self, data):
        request_id = data['request_id']
        self.parent.kill_exec_timer(request_id)
        self.parent.mark_request_done(request_id)

    async def on_delete_experiment(self, data):
        request_id = data['request_id']
        self.parent.kill_exec_timer(request_id)
        self.parent.mark_request_done(request_id)

    async def on_delete_project(self, data):
        request_id = data['request_id']
        self.parent.kill_exec_timer(request_id)
        self.parent.mark_request_done(request_id)


class BaseTestClient(BaseServiceClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_alive = False
        self.done = {}
        self.timers = {}
        self.reset()
        self.projects_root = None
        self.projects = None
        self.stop_event = Event()
        self.cancel_event = Event()

    def reset(self):
        self.done.clear()
        for t in self.timers.values():
            t.cancel()
        self.timers.clear()
        self.cancel_message = ''
        self.target_exception = None
    
    async def init_service(self):
        # global service_q
        # service_q = CacheQ('request_id/viz_type')
        pass

    async def service_main(self):
        self.is_alive = True
        while not self.stop_event.is_set() and not self.cancel_event.is_set():
            await asyncio.sleep(.5)
        self.is_alive = False
        if self.cancel_event.is_set():
            raise InterruptedError(self.cancel_message)


    # helpers
    def run_until_complete(self):
        try:
            asyncio.run(self.run())
            print('Success')
        # except KeyboardInterrupt:
        #     print(f"KeyboardInterrupt for {self.__class__.__name__}")
        #     raise
        # except InterruptedError as e:
        #     print(f"Failure: {str(e)}")
        #     raise
        # except Exception as e:
        #     print(f"Exception '{str(e)}' for {self.__class__.__name__}")
        #     raise
        except Exception as e:
            self.target_exception = e
            raise
        finally:
            print(f'Service stopped.')
        return

    def set_test_params(self, fname: str=None, t_range_max: int=None, max_exec_time: int=None):
        # read test params from sample attributes file
        # encode test params into request_id via corresponding template
        t_range_max = t_range_max or samples.get(fname, {}).get('t_range_max')
        max_exec_time = max_exec_time or samples.get(fname, {}).get('max_exec_time')
        res = f"{int(time.time())}_{t_range_max}_{max_exec_time}"
        return res

    def stop_client(self, reason='Client stopped'):
        self.stop_event.set()
        self.log(reason)

    def cancel_client(self, reason):
        self.cancel_message = reason
        self.cancel_event.set()
        self.log(reason)

    def mark_request_done(self, id):
        self.done[id] = True
        self.log(id)

    def create_exec_timer(self, id, seconds, reason):
        self.timers[id] = Timer(int(seconds), self.cancel_client, args=[reason,])
        self.timers[id].start()
        self.log(id)

    def kill_exec_timer(self, id):
        timer = self.timers.pop(id, None)
        if timer:
            timer.cancel()
            self.log(id)

    async def join_requests(self):
        while self.is_alive and not all(self.done.values()):
            await asyncio.sleep(0.3)
        self.log(list(self.done.keys()))

    async def emit_client_notification(self, name, value, *args, **kwargs):
        await self.ns_handler.emit_client_notification(name, value, *args, **kwargs)

    # decorators
    @decorator
    def track_request_id_completed(func, self, *args, **kwargs):
        # handler of decorated request will use request_id kwarg to mark it done, when the
        #  request is finished; self.join_requests() will join all the decorated requests
        self.done[kwargs['request_id']] = False
        return func(self, *args, **kwargs)

    @decorator
    def limit_exec_time(func, self, *args, **kwargs):
        # Limit execution by max_exec_time;
        # max_exec_time is encoded in request_id; for some tests exec time is not
        # important: if so, then requiest_id encoding skipped and default is 5 sec
        request_id = kwargs['request_id']
        try:
            _, _, _, max_exec_time = request_id.split('_')
        except:
            max_exec_time = 5
        self.create_exec_timer(request_id, max_exec_time, f'processing {func.__name__}({request_id} ...) exceeded max execution time of {max_exec_time} seconds')
        return func(self, *args, **kwargs)


    # test API
    @track_request_id_completed
    @limit_exec_time
    async def emit_coordinate_request(self, fname, **kwargs):
        await self.ns_handler.emit_client_notification(
                    'coordinate_request',
                    {'filename': fname,
                    'request_id': kwargs['request_id'],
                    'data_type': 'signal',
                    'dims': ['time'],
                    },
                    namespace=get_namespace(fname),
        )

    @track_request_id_completed
    @limit_exec_time
    async def emit_visualize_range(self, fname, **kwargs):
        await self.ns_handler.emit_client_notification(
                    'visualize_range',
                    {'filename': fname,
                    'request_id': kwargs['request_id'],
                    'mz_range': kwargs.get('mz_range', None),
                    't_range': kwargs.get('t_range', None),
                    # 'viz_types': ["spectrogram", "timeseries", "waterfall"],
                    'viz_types': kwargs.get('viz_types', ["spectrogram"]),
                    },
                    client_room=self.ns_handler.room_sid,
        )

    @track_request_id_completed
    @limit_exec_time
    async def emit_service_state(self, *args, **kwargs):
        await self.ns_handler.emit_client_notification(
                name='service_state',
                value={},
                request_id=kwargs['request_id'],
                )

    @track_request_id_completed
    @limit_exec_time
    async def emit_project_selected(self, pname, *args, **kwargs):
        await self.ns_handler.emit_client_notification(
                name='project_selected',
                value={'title': pname, },
                client_room=self.ns_handler.room_sid,
                request_id=kwargs['request_id'],
            )

    @track_request_id_completed
    @limit_exec_time
    async def emit_experiment_selected(self, pname, ename, *args, **kwargs):
        await self.ns_handler.emit_client_notification(
                name='experiment_selected',
                value={
                    'project': pname,
                    'title': ename,
                },
                client_room=self.ns_handler.room_sid,
                request_id=kwargs['request_id'],
            )

    @track_request_id_completed
    @limit_exec_time
    async def emit_save_project(self, pname, attrs, *args, **kwargs):
        await self.ns_handler.emit_client_notification(
                name='save_project',
                value={
                    'title': pname,
                    'attributes': attrs,
                },
                request_id=kwargs['request_id'],
            )

    @track_request_id_completed
    @limit_exec_time
    async def emit_save_experiment(self, pname, ename, attrs, template, *args, **kwargs):
        await self.ns_handler.emit_client_notification(
                name='save_experiment',
                value={
                    'project': pname,
                    'title': ename,
                    'attributes': attrs,
                    'sample_attributes_template': template,
                },
                request_id=kwargs['request_id'],
            )

    @track_request_id_completed
    @limit_exec_time
    async def emit_delete_experiment(self, pname, ename, *args, **kwargs):
        await self.ns_handler.emit_client_notification(
                name='delete_experiment',
                value={
                    'project': pname,
                    'experiment': ename,
                },
                request_id=kwargs['request_id'],
            )

    @track_request_id_completed
    @limit_exec_time
    async def emit_delete_project(self, pname, *args, **kwargs):
        await self.ns_handler.emit_client_notification(
                name='delete_project',
                value={
                    'project': pname,
                },
                request_id=kwargs['request_id'],
            )


def run_client():
    # Use run_client, when running client service from the terminal
    args = parse_cmd_args()
    client = BaseTestClient(args['url'],
                            args['port'],
                            (args.get('ns', '/'), BaseTestClientNamespace)
                           )
    try:
        client.run_until_complete()
    except:
        pass


def start_test_client_as_daemon(timeout=10):
    args = parse_cmd_args()
    client = BaseTestClient(args['url'],
                            args['port'],
                            (args.get('ns', '/'), BaseTestClientNamespace)
                           )
    client.daemon = Thread(target=client.run_until_complete)
    client.daemon.start()
    start = int(time.time())
    now = int(time.time())
    while not client.is_alive and now-start < timeout:
        asyncio.run(asyncio.sleep(.5))
        now = int(time.time())
    return client if now-start < timeout else None


def test_some_requests():
    # use this procedure for testing request combinations
    print('-- Start client')
    client = start_test_client_as_daemon()

    fname = 'TofDaq_Data_2021.08.02_01h01m01s'

    # print('-- Run coordinate_request')
    # # TODO: check coordinates - smth wrong here - see handler
    # def coordinate_request():
    #     max_exec_time = 7
    #     rq_suffix = client.set_test_params(fname, max_exec_time=max_exec_time)
    #     asyncio.run(client.emit_coordinate_request(fname, request_id=f'coordinates_{rq_suffix}'))
    # coordinate_request()

    print('-- Visualize full range')
    def visualize_full_range():
        rq_suffix = client.set_test_params(fname)
        asyncio.run(client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))
    visualize_full_range()

    # print('-- Visualize zoomed range')
    # # TODO: does not work either alone or consequently with full-range vis - to be fixed
    # def visualize_zoomed_range():
    #     max_exec_time = 30
    #     t_range_max = 10
    #     t_range=[5, t_range_max]
    #     mz_range=[100, 200]
    #     rq_suffix = client.set_test_params(fname, t_range_max=t_range_max, max_exec_time=max_exec_time)
    #     asyncio.run(client.emit_visualize_range(fname,
    #                                             request_id=f'zoom_{rq_suffix}',
    #                                             mz_range=mz_range,
    #                                             t_range=t_range))
    # visualize_zoomed_range()


    print('-- Run other requests...')
    # ...

    print('-- Wait all requests to be processed')
    asyncio.run(client.join_requests())
    client.stop_client('-- Stop client')


if __name__=='__main__':
    # run_client()  # Use it as main loop, when running client service from the terminal

    test_some_requests()    # use it for testing request combinations
