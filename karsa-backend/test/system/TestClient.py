#!/bin/pyton3

import time
import asyncio
from karsalib import parse_cmd_args, \
                    BaseClientNamespace, BaseServiceClient, CacheQ
from multiprocessing import Event



service_q = None
samples = {'TofDaq_Data_2021.07.23_02h13m40s': {'t_range_max': 30, 'max_acq_duration': 1}}



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
        r_type, t_start, t_range_max, max_acq_duration = request_id.split('_')
        done = int(t_range_max) <= int(t_range_1)
        self.parent.done[request_id] = done
        proc_time = int(time.time()) - int(t_start)
        in_time =  proc_time < int(max_acq_duration)
        if not in_time:
            self.parent.cancel_event.set()
            raise Exception(request_id, f'overdue max_acq_duration: {proc_time} vs. {max_acq_duration}')
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
        self.log(data)
        # service_q.cache_put(data)
        done, in_time = self.check_request_finished(data)
        return data['cnt']

    async def on_figure_data(self, data):
        self.log(data)
        # service_q.cache_put(data)
        done, in_time = self.check_request_finished(data)



class TestClient(BaseServiceClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.done = {}
        self.cancel_event = Event()
    
    async def init_service(self):
        global service_q
        service_q = CacheQ('request_id/viz_type')


    # helpers
    def set_test_params(self, fname: str, t_range_max: int=None, max_acq_duration: int=None):
        # read data from sample attributes file
        t_range_max = t_range_max or samples[fname]['t_range_max']
        max_acq_duration = max_acq_duration or samples[fname]['max_acq_duration']
        res = f"{int(time.time())}_{t_range_max}_{max_acq_duration}"
        return res

    # test API
    async def test_coordinate_request(self, fname, **kwargs):
        self.done[kwargs['request_id']] = False
        await self.ns_handler.emit_client_notification(
                    'coordinate_request',
                    {'filename': fname,
                    'request_id': kwargs['request_id'],
                    'data_type': 'signal',
                    'dims': ['time'],
                    },
                    namespace=get_namespace(fname),
        )

    async def test_visualize_range(self, fname, **kwargs):
        self.done[kwargs['request_id']] = False
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
        # rq_suffix = self.set_test_params(fname, t_range_max=10, max_acq_duration=5)
        # await self.test_visualize_range(fname,
        #                                 request_id=f'zoom_{rq_suffix}',
        #                                 mz_range=[100, 200],
        #                                 t_range=[5, 10])

        await asyncio.sleep(2)
        while not all(self.done.values()) or not self.cancel_event.is_set():
            await asyncio.sleep(.5)


def run():
    args = parse_cmd_args()
    client = TestClient(args['url'],
                        args['port'],
                        (args.get('ns', '/'), TestClientNamespace)
                        )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        print(f'Service stopped.')
    return



if __name__=='__main__':
    run()
