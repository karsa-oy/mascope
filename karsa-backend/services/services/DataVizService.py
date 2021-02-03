# -*- coding: utf-8 -*-
"""Data Visualization Service

This script runs the data visualization service for Karsa Tarkka TOF system.

DataVizService gets acquisition notifications from TOFService
It collects MS data, generates images in real time and pushes them to subscribers.

The script runs a client socket to connect to a Router; via the Router it receives
acquisition notifications, run figure generators in corresponding threads, and sends
the images to subscribers

Created on Fri Apr 17 11:35:57 2020
"""

import inspect
import asyncio
import numpy as np
import dask.array as da

from copy import deepcopy
from multiprocessing import (
                        Queue,
                        cpu_count
                        )
from datetime import timedelta
from queue import Empty

from karsalib import BaseClientNamespace, BaseServiceClient, parse_cmd_args
from karsatof.kworker import HeatmapGenerator, SpecTraceGenerator
from karsatof.kcollector import ExtendableDataArray
from karsatof.kimage import (
                    DEFAULT_TRACE,
                    convert_base64_to_img,
                    convert_to_base64,
                    hstack_imgs,
                    )


NO_DATA_LOGGING_DEFAULT = True
client = None
visualizers = {}
tps_visualizers = {}



def viz_cache_get_keys(viz_cache, data):
    sid = data['cookies']['src_sid'][0]
    fname = data['value'].get('filename')
    mz_range = data['value'].get('mz_range')
    t_range = data['value'].get('t_range')
    ranges = str([(mz_range or []) , (t_range or [])])
    return sid, fname, ranges, mz_range, t_range

def viz_cache_get(viz_cache, data):
    sid, fname, ranges, _, _ = viz_cache_get_keys(viz_cache, data)
    try:
        return viz_cache[sid][fname][ranges]
    except KeyError:
        return None

def viz_cache_put(viz_cache, data, viz):
    sid, fname, ranges, _, _ = viz_cache_get_keys(viz_cache, data)
    if sid not in viz_cache:
        viz_cache[sid] = {}
    if fname not in viz_cache[sid]:
        viz_cache[sid][fname] = {}
    viz_cache[sid][fname][ranges] = viz

def viz_cache_pop(viz_cache, data):
    """
    Method for releasing viz_cached resource. The value is released
    by presence of a corresponding sid/fname/ranges key in the data
    """
    sid, fname, ranges, mz_range, t_range = viz_cache_get_keys(
                                                            viz_cache,
                                                            data
                                                            )
    res = None
    try:
        if fname:
            if not mz_range and not t_range:
                res = viz_cache[sid].pop(fname)
            else:
                res = viz_cache[sid][fname].pop(ranges)
        else:
            res = viz_cache.pop(sid)
    except KeyError:
        res = None
    return res


def merge_heatmap_slices(slices):
    slice_images = []
    for slc in slices:
        img_str = slc.get('img')
        img = convert_base64_to_img(img_str)
        slice_images.append(img)
    full_img = hstack_imgs(slice_images)
    #full_img_str = convert_to_base64(full_img)
    return full_img




class DataVizServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    rooms = ['acquisition_coordinates',
             'acquired_spectrum',
             'acquired_tps_data',
             'acquisition_finished',
             'data_stream_coordinates',
             'data_stream_finished',
             'loaded_spectrum',
             'loaded_tps_data',
             'service_state',
             'stop_visualize_range',
             'target_to_load',
             'tps_data_stream_coordinates',
             'tps_data_stream_finished',
             'tps_parameter_info',
             'tps_parameters_selected',
             'visualize_range',
             ]

    # ========== UI requests ==========
    async def on_visualize_range(self, data):
        """ Images with new 't_range' and/or 'mz_range' requested

        Parameters
        ----------
        data : dict(name, value, cookies, no_logging, no_data_logging...)
               value: JSON data from UI, keys: 'filename', 't_range', 'mz_range'
        """
        await self.emit_client_notification('data_request',
                                            data['value'],
                                            cookies=data['cookies'],
                                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                                            )
    
    async def on_stop_visualize_range(self, data):
        """ Stop visualization, if still running; use filename and ranges as input:
            - if none specified, stop all visualizations for the client;
            - with file name specified, stop the file visualization;
            - with ranges specified, stop visualizing current ranges;

        Parameters
        ----------
        data : dict(name, value, cookies, no_logging, no_data_logging...)
               value: JSON data from UI, keys: 'filename', 't_range', 'mz_range'
        """
        await self.emit_client_notification('stop_data_request', data['value'], cookies=data['cookies'], no_data_logging=NO_DATA_LOGGING_DEFAULT)
        global visualizers
        global tps_visualizers

        visualizer = viz_cache_pop(visualizers, data)
        if isinstance(visualizer, SignalVisualizer):
            await visualizer.flush_visualizations(data['cookies'])
        tps_visualizer = viz_cache_pop(tps_visualizers, data)
        if isinstance(tps_visualizer, TPSVisualizer):
            await visualizer.flush_visualizations(data['cookies'])


    async def on_tps_parameters_selected(self, data):
        """TPS parameters selected from the dropdown
        """
        await self.emit_client_notification('tps_data_request',
                                            data['value'],
                                            cookies=data['cookies'],
                                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                                            )

    # ---------------------------------

    # ========== FileService notifications ==========
    async def on_data_stream_coordinates(self, data):
        set_figure_ranges = data['value'].get('set_figure_ranges', False)
        data['value']['set_figure_range'] = set_figure_ranges
        await self.on_acquisition_coordinates(data)

    async def on_loaded_spectrum(self, data):
        await self.on_acquired_spectrum(data)
        return data['value'].get('i')

    async def on_data_stream_finished(self, data):
        await self.on_acquisition_finished(data)
    
    async def on_tps_data_stream_coordinates(self, data):
        await self.on_tps_parameter_info(data)

    async def on_loaded_tps_data(self, data):
        await self.on_acquired_tps_data(data)
        return data['value'].get('i')

    async def on_tps_data_stream_finished(self, data):
        return
    # -----------------------------------------------


    # ========== TOFService notifications ==========
    async def on_acquisition_coordinates(self, data):
        global client
        global visualizers

        value = data['value']
        set_figure_ranges = value.get('set_figure_ranges', True)
        filename = value.get('filename')

        mz = np.frombuffer( value.get('mz'), dtype=np.float32 )
        t = np.frombuffer( value.get('time'), dtype=np.float32 )
        
        mz_range = [ float(mz[0]), float(mz[-1]) ]
        t_range =  [ float(t[0]),  float(t[-1])  ]

        visualizer = SignalVisualizer(filename,
                                      client.heatmap_gen_input_q,
                                      client.spec_trace_gen_input_q
                                      )
        # Initialize visualizer cache
        visualizer.init_array(dims=('mz', 'time'),
                              data=None,
                              coords=[mz, []],
                              name='signal'
                              )
        viz_cache_put(visualizers, data, visualizer)
        if set_figure_ranges:
            # Set UI figure ranges
            await self.emit_client_notification(
                                'figure_ranges',
                                {'filename': filename,
                                 'mz_range': mz_range,
                                 't_range': t_range,
                                 },
                                cookies=data['cookies'],
                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                )


    async def on_acquired_spectrum(self, data):
        global visualizers
        value = data['value']
        visualizer = viz_cache_get(visualizers, data)
        if not visualizer:  # data request was cancelled
            return
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
        viz_cache_put(tps_visualizers, data, visualizer)

        if set_tps_parameters:
            dropdown_items = [{'label': info,
                               'value': i
                               } for i, info in enumerate(tps_info)
                            ]            
            await self.emit_client_notification(
                            'tps_parameters',
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
        visualizer = viz_cache_get(tps_visualizers, data)
        if not visualizer:  # data request was cancelled
            return
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
        #visualizer = viz_cache_pop(visualizers, data)
        visualizer = viz_cache_get(visualizers, data)
        if isinstance(visualizer, SignalVisualizer):
            await visualizer.flush_visualizations(data['cookies'])
            if len(visualizer.heatmap_slices):
                full_heatmap = merge_heatmap_slices(visualizer.heatmap_slices)
                full_heatmap_str = convert_to_base64(full_heatmap)
                image_data = {'filename': visualizer.filename,
                              'img_filename': 'heatmap.png',
                              'img': full_heatmap_str
                              }
                await self.emit_client_notification(
                                    'image_to_save',
                                    image_data,
                                    cookies=data['cookies'],
                                    no_data_logging=NO_DATA_LOGGING_DEFAULT
                                    )
            for i, spec_trace in enumerate(visualizer.spec_traces):
                image_data.update({'img_filename': 'spec%s.png' %i,
                                   'img': spec_trace['img']
                                   })
                await self.emit_client_notification(
                                    'image_to_save',
                                    image_data,
                                    cookies=data['cookies'],
                                    no_data_logging=NO_DATA_LOGGING_DEFAULT)
            
    # ----------------------------------------------


class SignalVisualizer(ExtendableDataArray):

    def __init__(self,
                 filename,
                 heatmap_generator_q,
                 spec_trace_generator_q,
                 step=10
                 ):
        ExtendableDataArray.__init__(self, array_module=da)
        self.filename = filename
        self.heatmap_generator_q = heatmap_generator_q
        self.spec_trace_generator_q = spec_trace_generator_q
        self.step = step
        
        self.heatmap_slices = []
        self.spec_traces = []

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]",
              *arg,
              **kwarg
              )

    async def extend_visualizations(self, cookies):
        """Generate visualizations for new data.
        """

        if self.data_array.shape[1] < (self.step + 1):
            return

        # Set ranges
        t0 = float( self.data_array.time[0] ) * 1e-9 # [ns]->[s]
        t1 = float( self.data_array.time[-1] ) * 1e-9
        t_range = [t0, t1]

        mz0 = float(self.data_array.mz[0])
        mz1 = float(self.data_array.mz[-1])
        mz_range = [mz0, mz1]
        
        #
        arr_to_viz = self.data_array[:, :]

        # Put to queue
        self.heatmap_generator_q.put({'data': arr_to_viz,
                                      'filename': self.filename,
                                      'mz_range': mz_range,
                                      't_range': t_range,
                                      'cookies': cookies,
                                      })
        self.spec_trace_generator_q.put({'data': arr_to_viz,
                                         'filename': self.filename,
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
        await client.emit_client_notification('timeseries_figure_data',
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
        await client.emit_client_notification('timeseries_figure_data',
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



class DataVizServiceClient(BaseServiceClient):
    async def init_service(self):
        self.heatmap_gen_input_q = Queue()
        self.spec_trace_gen_input_q = Queue()
        self.heatmap_q = Queue()
        self.spec_trace_q = Queue()
        self.heatmap_generators = []
        self.spec_trace_generators = []

        n_jobs = int( cpu_count() / 2 )
        for i in range(n_jobs):
            self.log("Spawning HeatmapGenerator %s/%s" %(i+1, n_jobs))
            hm_gen = HeatmapGenerator(self.heatmap_gen_input_q,
                                      self.heatmap_q
                                      )
            hm_gen.start()
            self.heatmap_generators.append(hm_gen)
            await self.sio.sleep(1)
            self.log("Spawning SpecTraceGenerator %s/%s" %(i+1, n_jobs))
            st_gen = SpecTraceGenerator(self.spec_trace_gen_input_q,
                                        self.spec_trace_q
                                        )
            st_gen.start()
            self.spec_trace_generators.append(st_gen)
            await self.sio.sleep(1)


    async def service_main(self):
        global visualizers
        
        while True:
            # Check queues for new images
            try:
                heatmap_slice = self.heatmap_q.get_nowait()
            except Empty:
                heatmap_slice = None
            try:
                spec_trace = self.spec_trace_q.get_nowait()
            except Empty:
                spec_trace = None
            if heatmap_slice is None and spec_trace is None:
                # No new images, try again soon
                await self.sio.sleep(.1)
                continue

            # Got at least something
            if heatmap_slice is not None:
                cache_ref = dict(cookies = heatmap_slice['cookies'],
                                 value = dict(filename=heatmap_slice['filename'])
                                 )
                visualizer = viz_cache_get(visualizers, cache_ref)
                if visualizer:
                    visualizer.heatmap_slices.append(heatmap_slice)
                cookies = heatmap_slice.pop('cookies')
                await self.emit_client_notification(
                                'heatmap_figure_data',
                                heatmap_slice,
                                cookies=cookies,
                                no_data_logging=True
                                )
            if spec_trace is not None:
                cache_ref = dict(cookies = spec_trace['cookies'],
                                 value = dict(filename=spec_trace['filename'])
                                 )
                visualizer = viz_cache_get(visualizers, cache_ref)
                if visualizer:
                    visualizer.spec_traces.append(spec_trace)
                cookies = spec_trace.pop('cookies')
                await self.emit_client_notification(
                                'spec_stack_figure_data',
                                spec_trace,
                                cookies=cookies,
                                no_data_logging=True
                                )

        # Terminate image generators
        [p.terminate() for p in self.heatmap_generators]
        [p.terminate() for p in self.spec_trace_generators]
        await self.sio.disconnect()



def run():
    global client
    client = DataVizServiceClient(*parse_cmd_args(),
                                  DataVizServiceNamespace
                                  )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
