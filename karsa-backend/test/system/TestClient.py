#!/bin/pyton3

import time
import asyncio
from decorator import decorator
from karsalib import parse_cmd_args, \
                    BaseClientNamespace, BaseServiceClient, CacheQ
from multiprocessing import Event
from threading import Timer



# service_q = None
samples = {'TofDaq_Data_2021.07.23_02h13m40s': {'t_range_max': 30, 'max_exec_time': 3}}



def get_namespace(filename):
    return '/' + filename.split('_')[0]

class TestClientNamespace(BaseClientNamespace):
    endpoints = []
    endpoints_room_sid = [
        # 'loaded_coordinates',   # response to coordinate_request
        'loaded_data',          # full-size image
        'figure_data',          # zoomed-in image
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

    def check_request_finished(self, data):
        request_id = data['value']['request_id']
        t_range_1 = data['value']['t_range'][1]
        r_type, t_start, t_range_max, max_exec_time = request_id.split('_')
        done = int(t_range_max) <= int(t_range_1)
        self.parent.done[request_id] = done
        proc_time = int(time.time()) - int(t_start)
        in_time =  proc_time < int(max_exec_time)
        if done:
            self.parent.kill_exec_timer(request_id)
        return done, in_time


    # test validators
    
    # # TODO: smth wrong with this notificaiton: we just need ranges, but it gives huge coords array
    # async def on_loaded_coordinates(self, data):
    #     self.log(data['value']['request_id'])
    #     self.log(data['value']['data_type'])
    #     self.log(data['value']['dims'])     #
    #     # self.log(data['value']['coordinates'])  -  why so long???
    #     # service_q.cache_put(data)

    async def on_loaded_data(self, data):
        self.log(data.keys())
        # service_q.cache_put(data)
        _, _ = self.check_request_finished(data)
        return data['cnt']

    async def on_figure_data(self, data):
        self.log(data.keys())
        # service_q.cache_put(data)
        _, _ = self.check_request_finished(data)



class TestClient(BaseServiceClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.done = {}
        self.timers = {}
        self.cancel_event = Event()
        self.cancel_message = ''
    
    async def init_service(self):
        # global service_q
        # service_q = CacheQ('request_id/viz_type')
        pass


    def cancel_request(self, reason):
        self.cancel_message = reason
        self.cancel_event.set()

    def create_exec_timer(self, id, seconds, reason):
        self.timers[id] = Timer(int(seconds), self.cancel_request, args=[reason,])
        self.timers[id].start()
        print('AAAAA timer started', id)

    def kill_exec_timer(self, id):
        timer = self.timers.get(id)
        if timer:
            timer.cancel()
            self.timers.pop(id)
            print('AAAAA timer killed', id)


    # decorators
    @decorator
    def wait_until_request_completed(func, self, *args, **kwargs):
        # create done=False flag for this request; corresponding
        # request handler will set done=True, when request is finished
        self.done[kwargs['request_id']] = False
        return func(self, *args, **kwargs)

    @decorator
    def limit_exec_time(func, self, *args, **kwargs):
        request_id = kwargs['request_id']
        _, _, _, max_exec_time = request_id.split('_')
        self.create_exec_timer(request_id, max_exec_time, f'{request_id} exceeded max execution time {max_exec_time} seconds')
        return func(self, *args, **kwargs)


    # helpers
    def set_test_params(self, fname: str, t_range_max: int=None, max_exec_time: int=None):
        # read test params from sample attributes file
        # encode test params into request_id via corresponding template
        t_range_max = t_range_max or samples[fname]['t_range_max']
        max_exec_time = max_exec_time or samples[fname]['max_exec_time']
        res = f"{int(time.time())}_{t_range_max}_{max_exec_time}"
        return res


    # test API
    @wait_until_request_completed
    @limit_exec_time
    async def test_coordinate_request(self, fname, **kwargs):
        await self.ns_handler.emit_client_notification(
                    'coordinate_request',
                    {'filename': fname,
                    'request_id': kwargs['request_id'],
                    'data_type': 'signal',
                    'dims': ['time'],
                    },
                    namespace=get_namespace(fname),
        )

    @wait_until_request_completed
    @limit_exec_time
    async def test_visualize_range(self, fname, **kwargs):
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


    async def service_main(self):
        fname = 'TofDaq_Data_2021.07.23_02h13m40s'

        # check coordinates - smth wrong here
        # rq_suffix = self.set_test_params(fname)
        # await self.test_coordinate_request(fname, request_id='coordinates_{rq_suffix}')

        # this one works ok
        rq_suffix = self.set_test_params(fname)
        await self.test_visualize_range(fname, request_id=f"fullrange_{rq_suffix}")

        # this one is unstable
        # t_start = int(time.time())
        # t_range_max = 10
        # rq_suffix = self.set_test_params(fname, t_range_max=10, max_exec_time=5)
        # await self.test_visualize_range(fname,
        #                                 request_id=f'zoom_{rq_suffix}',
        #                                 mz_range=[100, 200],
        #                                 t_range=[5, 10])

        await asyncio.sleep(2)
        while not all(self.done.values()) and not self.cancel_event.is_set():
            await asyncio.sleep(.5)
        if self.cancel_event.is_set():
            raise InterruptedError(self.cancel_message)


def run():
    args = parse_cmd_args()
    client = TestClient(args['url'],
                        args['port'],
                        (args.get('ns', '/'), TestClientNamespace)
                        )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
        print('Success')
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except InterruptedError as e:
        print(f"Failure: {str(e)}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        print(f'Service stopped.')
    return



if __name__=='__main__':
    run()
