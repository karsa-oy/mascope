# -*- coding: utf-8 -*-
"""Data Visualization Service

This script runs the data visualization service for Karsa Tarkka TOF system.

DataVizService gets acquisition notifications from TOFService
It collects MS data, generates images in real time and pushes them to subscribers.

Running this script will start a client socket to receive acquisition notifications
and run figure generators in corresponding threads.

Created on Fri Apr 17 11:35:57 2020
"""

import os
import sys
import getopt
import inspect
import xarray
import socketio
import asyncio
import numpy as np
import dask.array as da

from copy import copy, deepcopy
from threading import Thread
from multiprocessing import (
                        Event,
                        Queue,
                        cpu_count
                        )
from datetime import timedelta
from queue import Empty

from helpers import BaseClientNamespace
from karsatof.kevent import KEvent
from karsatof.kworker import HeatmapGenerator, SpecTraceGenerator
from karsatof.kcollector import ExtendableDataArray
from karsatof.kimage import (
                    DEFAULT_TRACE,
                    gen_timeseries_trace,
                    gen_ridge_traces,
                    gen_heatmap_image,
                    gen_spec_image,
                    stack_spec_images,
                    gen_spec_stack_image,
                    convert_to_base64,
                    merge_heatmap_slices,
                    )
from karsatof.kutil import (SubscriptableQueue,
                            QueueSubscription
                            )

NO_DATA_LOGGING_DEFAULT = True
class DataVizRouterNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    rooms = ['acquisition_coordinates',
             'acquired_spectrum',
             'acquired_tps_data',
             'acquisition_finished',
             'data_stream_coordinates',
             'loaded_spectrum',
             'loaded_tps_data',
             'data_stream_finished',
             'service_state',
             'target_to_load',
             'tps_data_stream_coordinates',
             'tps_data_stream_finished',
             'tps_parameter_info',
             'tps_parameters_selected',
             'visualize_range'
             ]

    # ========== UI requests ==========
    async def on_visualize_range(self, data):
        """ Images with new 't_range' and/or 'mz_range' requested

        Parameters
        ----------
        data : dict(name, value, cookies, no_logging, no_data_logging...)
               value: JSON data from UI, keys: 'filename', 't_range', 'mz_range'
        """
        await emit_client_notification('data_request', data['value'], cookies=data['cookies'], no_data_logging=NO_DATA_LOGGING_DEFAULT)
    
    async def on_tps_parameters_selected(self, data):
        """TPS parameters selected from the dropdown
        """
        await emit_client_notification('tps_data_request', data['value'], cookies=data['cookies'], no_data_logging=NO_DATA_LOGGING_DEFAULT)

    # ---------------------------------

    # ========== FileService notifications ==========
    async def on_data_stream_coordinates(self, data):
        set_figure_ranges = data['value'].get('set_figure_ranges', False)
        data['value']['set_figure_range'] = set_figure_ranges
        await self.on_acquisition_coordinates(data)

    async def on_loaded_spectrum(self, data):
        await self.on_acquired_spectrum(data)

    async def on_data_stream_finished(self, data):
        await self.on_acquisition_finished(data)
    
    async def on_tps_data_stream_coordinates(self, data):
        await self.on_tps_parameter_info(data)

    async def on_loaded_tps_data(self, data):
        await self.on_acquired_tps_data(data)

    async def on_tps_data_stream_finished(self, data):
        return
    # -----------------------------------------------

    # ========== TOFService notifications ==========
    async def on_acquisition_coordinates(self, data):
        value = data['value']
        set_figure_ranges = value.get('set_figure_ranges', True)
        filename = value.get('filename')

        mz = np.frombuffer( value.get('mz'), dtype=np.float32 )
        t = np.frombuffer( value.get('time'), dtype=np.float32 )
        # t_range = value.get('t_range')
        
        mz_range = [ float(mz[0]), float(mz[-1]) ]
        t_range =  [ float(t[0]),  float(t[-1])  ]

        global visualizers
        global heatmap_generator_q
        global spec_trace_generator_q

        visualizer = SignalVisualizer(heatmap_generator_q,
                                      spec_trace_generator_q
                                      )
        # Initialize visualizer cache
        visualizer.init_array(dims=('mz', 'time'),
                              data=None,
                              coords=[mz, []],
                              name='signal'
                              )

        cache_key = derive_cache_key(value)

        if cache_key in visualizers.keys():
            raise Exception("on_acquisition_coordinates: key %s " % cache_key + 
                            "already in cache."
                            )
        
        visualizers.update({cache_key: visualizer
                            })

        if set_figure_ranges:
            # Set UI figure ranges
            await emit_client_notification('figure_ranges',
                                           {'filename': filename,
                                            'mz_range': mz_range,
                                            't_range': t_range,
                                            },
                                            cookies=data['cookies'],
                                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                                           )
    
    async def on_acquired_spectrum(self, data):
        value = data['value']
        # speci = value.get('i')
        # self.log(speci)

        global visualizers
        cache_key = derive_cache_key(value)
        visualizer = visualizers.get(cache_key)
        # Extend signal cache
        spec = np.frombuffer( value.get('spec'), dtype=np.float32 )
        spec = spec.reshape(-1, 1)
        ti = value.get('t')
        td = np.array( [timedelta(seconds=ti)] ) # Convert to timedelta
        mz = visualizer.data_array.mz
        await visualizer.extend_array(spec,
                                      [mz, td],
                                      'time'
                                      )
        await visualizer.extend_visualizations(data['cookies'])


    async def on_tps_parameter_info(self, data):
        value = data['value']
        tps_info = value.get('tps_info')
        set_tps_parameters = value.get('set_tps_parameters', True)

        visualizer = TPSVisualizer()

        # Initialize visualizer cache
        visualizer.init_array(dims=('parameter', 'time'),
                              data=None,
                              coords=[tps_info, []],
                              name='tps'
                              )

        global tps_visualizers
        cache_key = derive_cache_key(value)
        tps_visualizers.update({cache_key: visualizer
                                })

        if set_tps_parameters:
            dropdown_items = [{'label': info,
                               'value': i
                               } for i, info in enumerate(tps_info)
                            ]            
            await emit_client_notification('tps_parameters',
                                           dropdown_items,
                                           cookies=data['cookies'],
                                           no_data_logging=NO_DATA_LOGGING_DEFAULT
                                           )

    async def on_acquired_tps_data(self, data):
        value = data['value']
        # speci = value.get('i')
        # self.log(speci)

        global tps_data

        global tps_visualizers
        visualizer = tps_visualizers.get( derive_cache_key(value) )
        # Extend signal cache
        tps_data = np.frombuffer( value.get('tps_data'), dtype=np.float32 )
        tps_data = tps_data.reshape(-1, 1)
        ti = value.get('t')
        td = np.array( [timedelta(seconds=ti)] ) # Convert to timedelta
        parameter = visualizer.data_array.parameter

        return #XXX

        await visualizer.extend_array(tps_data,
                                      [parameter, td],
                                      'time',
                                      )
        await visualizer.extend_visualizations(data['cookies'])


    async def on_acquisition_finished(self, data):
        global visualizers
        cache_key = derive_cache_key(data['value'])
        visualizer = visualizers.pop(cache_key)
        # Flush visualizer
        await visualizer.flush_visualizations(data['cookies'])
    # ----------------------------------------------

        

# ---------- Functions to emit to UI ----------
# async def initialize_timeseries_figure(full_t_range, traces=[]):
#     timeseries_data = {"xrange": full_t_range, 
#                        "yrange": [0, 1],
#                        'traces': traces}
#     await emit_client_notification('timeseries_figure_data',
#                                    timeseries_data,
#                                    cookies=?
#                                    no_data_logging=True
#                                    )
    

# ========== Class definitions ==========

class SignalVisualizer(ExtendableDataArray):

    def __init__(self, heatmap_generator_q, spec_trace_generator_q, step=10):

        ExtendableDataArray.__init__(self, array_module=da)
        self.heatmap_generator_q = heatmap_generator_q
        self.spec_trace_generator_q = spec_trace_generator_q
        
        self.step = step

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    async def extend_visualizations(self, cookies):
        """Generate visualizations for new data.
        """

        if self.data_array.shape[1] < (self.step + 1):
            return

        # Set ranges
        t0 = float( self.data_array.time[0] ) * 1e-9
        t1 = float( self.data_array.time[-1] ) * 1e-9
        t_range = [t0, t1]

        mz0 = float(self.data_array.mz[0])
        mz1 = float(self.data_array.mz[-1])
        mz_range = [mz0, mz1]
        
        #
        arr_to_viz = self.data_array[:, :]

        # Put to queue
        self.heatmap_generator_q.put({'data': arr_to_viz,
                                      'mz_range': mz_range,
                                      't_range': t_range,
                                      'cookies': cookies,
                                      })
        self.spec_trace_generator_q.put({'data': arr_to_viz,
                                         'mz_range': mz_range,
                                         't_range': t_range,
                                         'cookies': cookies,
                                         })

        # Timeseries trace
        x = list( arr_to_viz.time.values.astype(float) * 1e-9 )
        y = list( arr_to_viz.sum('mz').values.astype(float) )
        ts_trace = deepcopy(DEFAULT_TRACE)
        ts_trace.update({'name': 'TIC [%.2f, %.2f]' %(mz0, mz1),
                         'x': x,
                         'y': y
                         }
                        )
        timeseries_data = {'traces': [ts_trace],
                           'mz_range': mz_range,
                           }
        await emit_client_notification('timeseries_figure_data',
                                       timeseries_data,
                                       cookies=cookies,
                                       no_data_logging=NO_DATA_LOGGING_DEFAULT
                                       )
        await self.reset_array()

    async def reset_array(self):
        # Reset signal cache, leave the latest spec
        last_spec = self.data_array[:, -1].values.reshape(-1, 1)
        last_t = self.data_array.time[-1].item() * 1e-9
        last_td = timedelta(seconds=last_t)
        self.init_array(dims=('mz', 'time'),
                        data=None,
                        coords=[self.data_array.mz, []],
                        name='signal'
                        )
        await self.extend_array(last_spec,
                                [self.data_array.mz, [last_td]],
                                'time'
                                )

    async def flush_visualizations(self, cookies):
        if self.data_array.shape[1] <= 1:
            return
        self.step = 0
        await self.extend_visualizations(cookies)
        

class TPSVisualizer(ExtendableDataArray):

    def __init__(self, tps_trace_queue=Queue(), step=10):

        ExtendableDataArray.__init__(self, array_module=da)

        self.trace_queue = tps_trace_queue
        self.step = step

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    async def extend_visualizations(self, cookies):
        """Generate visualizations for new data.
        """

        if self.data_array.shape[1] < (self.step+1):
            return

        # Set ranges
        t0 = float( self.data_array.time[0] ) * 1e-9
        t1 = float( self.data_array.time[self.step] ) * 1e-9
        t_range = [t0, t1]
        
        #
        selected_parameters = [self.data_array.parameter[0].item()]
        arr_to_viz = self.data_array[:, 0:self.step]
        arr_to_viz = arr_to_viz.loc[selected_parameters]

        # Timeseries trace
        x = list( arr_to_viz.time.values.astype(float) * 1e-9 )
        y = list( arr_to_viz.values.astype(float) )
        ts_trace = deepcopy(DEFAULT_TRACE)
        ts_trace.update({'name': selected_parameters,
                         'x': x,
                         'y': y,
                         'yaxis': 'y2'
                         }
                        )
        timeseries_data = {'traces': [ts_trace], }
        await emit_client_notification('timeseries_figure_data',
                                       timeseries_data,
                                       cookies=cookies,
                                       no_data_logging=NO_DATA_LOGGING_DEFAULT
                                       )

        # Reset signal cache, leave the last column
        last_col = self.data_array[:, -1].values.reshape(-1, 1)
        last_t = self.data_array.time[-1].item() * 1e-9
        last_td = timedelta(seconds=last_t)
        self.init_array(dims=self.data_array.dims,
                        data=None,
                        coords=[self.data_array.coords[self.data_array.dims[0]],
                                []
                                ],
                        name=self.data_array.name
                        )
        await self.extend_array(last_col,
                                [self.data_array.coords[self.data_array.dims[0]],
                                [last_td]
                                ],
                                'time'
                                )


# ---------------------------------------

# ========== Helper functions ==========
def derive_cache_key(data):
    """Generate cache key by combining filename and mz_range

    Parameters
    ----------
    data : dict
        JSON data with keys 'filename' (required) and
        'mz_range' (optional).

    Returns
    -------
    str
        Cache key
    """

    filename = data.get('filename')
    
    mz_range = data.get('mz_range', None)
    t_range = data.get('t_range', None)

    cache_key = filename
    if mz_range is None:
        cache_key += '[]'
    else:
        cache_key += '[%.1f,%.1f]' % (mz_range[0], mz_range[1])

    if t_range is None:
        cache_key += '[]'
    else:
        cache_key += '[%.1f,%.1f]' % (t_range[0], t_range[1])

    return cache_key

async def emit_client_notification(name, value, **kwarg):
    global root_ns
    await root_ns.emit_client_notification(name, value, **kwarg)

async def init_service(addr):
    global sio
    global root_ns
    # global tps_collector

    while True:
        try:
            print('Connecting to Router...')
            await sio.connect(addr, namespaces=['/', ])
            break
        except:
            print('Failed')
            await sio.sleep(1)

    global heatmap_generator_q
    global spec_trace_generator_q
    global heatmap_q
    global spec_trace_q
    global hm_ps
    global st_ps

    n_jobs = int( cpu_count() / 2 )

    for i in range(n_jobs):
        print("Spawning HeatmapGenerator %s/%s" %(i+1, n_jobs))
        hm_p = HeatmapGenerator(heatmap_generator_q, heatmap_q)
        hm_p.start()
        hm_ps.append(hm_p)
        await asyncio.sleep(1)
        print("Spawning SpecTraceGenerator %s/%s" %(i+1, n_jobs))
        st_p = SpecTraceGenerator(spec_trace_generator_q, spec_trace_q)
        st_p.start()
        st_ps.append(st_p)
        await asyncio.sleep(1)

    # tps_collector = KtpsCollector()


async def run_service(url, port):
    addr = f'{url}:{port}'
    if not addr.startswith('http'):
        addr = 'http://' + addr
    await init_service(addr)
    await main()
# --------------------------------------


async def main():
    """Main function
    
    Loop infinitely synchronized with acquisition
    
    Returns
    -------
    None.

    """
    global sio
    global heatmap_q
    global spec_trace_q

    heatmap_slices = []
    spec_traces = []


    # Main loop
    while True:
        # Check queues for new images
        try:
            heatmap_slice = heatmap_q.get_nowait()
        except Empty:
            heatmap_slice = None
        try:
            spec_trace = spec_trace_q.get_nowait()
        except Empty:
            spec_trace = None
        if heatmap_slice is None and spec_trace is None:
            # No new images, try again soon
            await sio.sleep(.1)
            continue

        # continue

        # Got at least something
        if heatmap_slice is not None:
            #heatmap_slices.append(heatmap_slice)
            cookies = heatmap_slice.pop('cookies')
            await emit_client_notification(
                            'heatmap_figure_data',
                            heatmap_slice,
                            cookies=cookies,
                            no_data_logging=True
                            )
        if spec_trace is not None:
            # spec_traces.append(spec_trace)
            cookies = spec_trace.pop('cookies')
            await emit_client_notification(
                            'spec_stack_figure_data',
                            spec_trace,
                            cookies=cookies,
                            no_data_logging=True
                            )

    # heatmap = merge_heatmap_slices(heatmap_slices)
    # heatmap.save('heatmap.png')

    global hm_ps
    [p.terminate() for p in hm_ps]
    global st_ps
    [p.terminate() for p in st_ps]

    await sio.disconnect()


sio = socketio.AsyncClient()
sio.register_namespace(DataVizRouterNamespace('/'))
root_ns = sio.namespace_handlers['/']

visualizers = {}
tps_visualizers = {}

heatmap_generator_q = Queue()
spec_trace_generator_q = Queue()
heatmap_q = Queue()
spec_trace_q = Queue()
hm_ps = []
st_ps = []


def parse_cmd_args():
    """Parse command line arguments
    Allowed command line arguments
    ------------------------------
    --url : string
        IP address (localhost)
    --port : int
        Server port (5010)
    """
    url = 'localhost'
    port = 5010
    opts, _ = getopt.getopt(
                    sys.argv[1:],
                    'o:v',
                    ['url=', 'port=', ]
                    )
    for opt, arg in opts:
        if opt=='--url':
            url = arg
        if opt=='--port':
            try:
                port = int(arg)
            except:
                print('Invalid command line argument: %s=%s' %(opt, arg))
    return url, port


def run():
    url, port = parse_cmd_args()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_service(url, port))


if __name__=='__main__':
    run()