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
import sqlite3

from copy import deepcopy
from multiprocessing import (
                        Queue,
                        cpu_count
                        )
from datetime import datetime, timedelta
from queue import Empty

from karsalib import BaseClientNamespace, BaseServiceClient, \
                     parse_cmd_args, get_client_notification_args
from karsatof.kworker import ImageGenerator
from karsatof.kcollector import ExtendableDataArray
from karsatof.kimage import (
                    DEFAULT_TRACE,
                    convert_base64_to_img,
                    convert_to_base64,
                    hstack_imgs,
                    )

NO_DATA_LOGGING_DEAULT = True
client = None
signal_cache = {}

generator_input_q = None # TODO:
generator_output_q = None # TODO:

in_memory_db = ':memory:'
test_db = datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss") + '.db'
con = sqlite3.connect(test_db) 
cur = con.cursor()

# Create viz table
cur.execute('''CREATE TABLE visualizations
               (filename text,
                viz_type text,
                t0 real,
                t1 real,
                mz0 real,
                mz1 real,
                t_resolution real,
                viz blob)
            ''')
            
# Create requests table            
cur.execute('''CREATE TABLE requests
               (filename text,
                viz_type text,
                t0 real,
                t1 real,
                mz0 real,
                mz1 real,
                t_resolution real,
                client_room text)
            ''')


def viz_cache_get(table,
                  fields,
                  filename=None,
                  viz_type=None,
                  t_range=None,
                  mz_range=None,
                  t_resolution=None,
                  client_room=None,
                  ):
    
    global con
    cur = con.cursor()
    
    args = []
    query = ''
    join_str = ''
    
    if filename:
        args.append(filename)
        query = join_str.join([query, 'filename = ?'])
        join_str = ' AND '

    if viz_type:
        args.append(viz_type)
        query = join_str.join([query, 'viz_type = ?'])
        join_str = ' AND '
        
    if t_range:
        args.extend(t_range)
        query = join_str.join([query, 't0 >= ? AND t1 <= ?'])
        join_str = ' AND '
        
    if mz_range:
        args.extend(mz_range)
        query = join_str.join([query, 'mz0 >= ? AND mz1 <= ?'])
        join_str = ' AND '
        
    if t_resolution:
        args.append(t_resolution)
        query = join_str.join([query, 't_resolution = ?'])
        join_str = ' AND '

    if client_room:
        args.append(client_room)
        query = join_str.join([query, 'client_room = ?'])
        join_str = ' AND '

    cur.execute('''SELECT {} FROM {} WHERE {}
                   ORDER BY t0 ASC
                '''.format(fields, table, query),
                args
                )
    return cur


def viz_cache_get_release_request(filename,
                                  viz_type,
                                  t_range,
                                  mz_range,
                                  t_resolution
                                  ):
    
    cur = viz_cache_get('requests',
                        'client_room',
                        filename,
                        viz_type,
                        t_range,
                        mz_range,
                        t_resolution
                        )
    
    client_rooms = []
    
    for row in cur:
        client_room, = row
        client_rooms.append(client_room)
        
        viz_cache_release('requests',
                          filename,
                          client_room,
                          viz_type,
                          t_range,
                          mz_range,
                          t_resolution
                          )
    
    return client_rooms


def viz_cache_process_requests(filename, t_range):

    signal_array = signal_cache[filename]

    # Get all pending requests for filename
    request_data_rows = viz_cache_get(
                            'requests',
                            'viz_type, t0, t1, mz0, mz1, t_resolution, client_room',
                            filename,
                            )

    for row in request_data_rows:
        print("[viz_cache_process_requests]: processing row: %s" %str(row))
        viz_type, t0, t1, mz0, mz1, t_resolution, client_room = row
        
        t0_chunk = t0
        t1_chunk = t0 + t_resolution
        
        while ( (t0_chunk >= t_range[0]) and
                (t1_chunk <= t_range[1]) ):
            print("chunk t_range: %s" %str((t0_chunk, t1_chunk)))
            arr_to_viz = signal_array.data_array.sel(
                                        time=slice(t0_chunk, t1_chunk),
                                        mz=slice(mz0, mz1)
                                        )
            # Put to queue to be visualized
            global generator_input_q
            generator_input_q.put({'data': arr_to_viz, # TODO: global q
                                   'filename': filename,
                                   'viz_type': viz_type,
                                   'mz_range': [mz0, mz1],
                                   't_range': [t0_chunk, t1_chunk],
                                   'y_range': [0, arr_to_viz.max().compute().item()], # TODO: better scaling
                                   't_resolution': t_resolution,
                                   'client_room': client_room,
                                   })
            if t1_chunk < t1:
                # Only part of request serverd, update request time range
                viz_cache_update('requests',
                                ['t0'],
                                [t1_chunk],
                                filename,
                                viz_type,
                                [t0, t1],
                                [mz0, mz1],
                                t_resolution,
                                client_room,
                                )
            else:
                # Request served fully, release rom cache
                viz_cache_release('requests',
                                  filename,
                                  client_room,
                                  viz_type,
                                  [t0, t1],
                                  [mz0, mz1],
                                  t_resolution
                                  )
            # Increment by t_resolution
            t0_chunk = t1_chunk
            t1_chunk = t0_chunk + t_resolution

def viz_cache_put(table,
                  filename,
                  viz_type,
                  t_range,
                  mz_range,
                  t_resolution,
                  *args
                  ):
    
    global con
    cur = con.cursor()
    
    values = (filename,
              viz_type,
              t_range[0],
              t_range[1],
              mz_range[0],
              mz_range[1],
              t_resolution,
              *args
              )
    
    cur.execute('''INSERT INTO {} VALUES (?,?,?,?,?,?,?,?)
                '''.format(table),
                values
                )    
    con.commit()
    

def viz_cache_release(table,
                      filename=None,
                      client_room=None,
                      viz_type=None,
                      t_range=None,
                      mz_range=None,
                      t_resolution=None
                      ):
        
    global con
    cur = con.cursor()
    
    args = []
    query = ''
    join_str = ''
    
    if filename:
        args.append(filename)
        query = join_str.join([query, 'filename = ?'])
        join_str = ' AND '
        
    if client_room:
        args.append(client_room)
        query = join_str.join([query, 'client_room = ?'])
        join_str = ' AND '

    if viz_type:
        args.append(viz_type)
        query = join_str.join([query, 'viz_type = ?'])
        join_str = ' AND '
        
    if t_range:
        args.extend(t_range)
        query = join_str.join([query, 't0 >= ? AND t1 <= ?'])
        join_str = ' AND '
        
    if mz_range:
        args.extend(mz_range)
        query = join_str.join([query, 'mz0 >= ? AND mz1 <= ?'])
        join_str = ' AND '
        
    if t_resolution:
        args.append(t_resolution)
        query = join_str.join([query, 't_resolution = ?'])
        join_str = ' AND '
        
    cur.execute('''DELETE FROM {} WHERE {}
                '''.format(table, query),
                args
                )
    con.commit()


def viz_cache_update(table,
                     fields,
                     values,
                     filename=None,
                     viz_type=None,
                     t_range=None,
                     mz_range=None,
                     t_resolution=None,
                     client_room=None,
                     *args,
                     ):

    global con
    cur = con.cursor()
    
    set_query = (', ').join(['{} = {}'.format(field, value)
                             for field, value in zip(fields, values)
                             ]
                            )
    args = []
    query = ''
    join_str = ''
    
    if filename:
        args.append(filename)
        query = join_str.join([query, 'filename = ?'])
        join_str = ' AND '

    if viz_type:
        args.append(viz_type)
        query = join_str.join([query, 'viz_type = ?'])
        join_str = ' AND '
        
    if t_range:
        args.extend(t_range)
        query = join_str.join([query, 't0 >= ? AND t1 <= ?'])
        join_str = ' AND '
        
    if mz_range:
        args.extend(mz_range)
        query = join_str.join([query, 'mz0 >= ? AND mz1 <= ?'])
        join_str = ' AND '
        
    if t_resolution:
        args.append(t_resolution)
        query = join_str.join([query, 't_resolution = ?'])
        join_str = ' AND '

    if client_room:
        args.append(client_room)
        query = join_str.join([query, 'client_room = ?'])
        join_str = ' AND '

    cur.execute('''UPDATE {} SET {} WHERE {}
                '''.format(table, set_query, query),
                args
                )
    con.commit()


def merge_heatmap_slices(slices):
    slice_images = []
    for slc in slices:
        img_str = slc.get('img')
        img = convert_base64_to_img(img_str)
        slice_images.append(img)
    full_img = hstack_imgs(slice_images)
    full_img_str = convert_to_base64(full_img)
    return full_img_str


class DataVizServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = ['acquisition_coordinates',
             'acquired_spectrum',
             'acquired_tps_data',
             'acquisition_finished',
             'data_stream_coordinates',
             'data_stream_finished',
             'heatmap_image',
             'loaded_spectrum',
             'loaded_tps_data',
             'service_state',
             'spec_trace_image',
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

        global generator_output_q # TODO:

        value = data['value']

        client_room = value['client_room']
        filename = value['filename']
        mz_range = value['mz_range']
        t_range = value['t_range']
        t_resolution = value.get('t_resolution')
        viz_type = value['viz_type']

        # Get already cached visualizations
        img_data_rows = viz_cache_get('visualizations',
                                      'viz, t0, t1',
                                      filename,
                                      viz_type,
                                      t_range,
                                      mz_range,
                                      t_resolution
                                      )
        # Emit cached visualizations and update request ranges accordingly
        img_strs = t0_chunk = t1_chunk = None
        for row in img_data_rows:
            
            img_str_row, t0_row, t1_row = row
            
            if t0_chunk is None:
                # Start new continuous chunk of images
                img_strs = []
                t0_chunk = t0_row
                if t0_chunk > t_range[0]:
                    # Gap in the beginning
                    # Make request for the gap
                    viz_cache_put('requests',
                                  filename,
                                  viz_type,
                                  [ t_range[0], t0_chunk ],
                                  mz_range,
                                  t_resolution,
                                  client_room
                                  )
            elif t0_row != t1_chunk: # t1 of previous slice != t0 of current one
                # Gap in the middle
                # Make request for the gap
                viz_cache_put('requests',
                              filename,
                              viz_type,
                              [t1_chunk, t0_chunk], # From previous t1 until current t0
                              mz_range,
                              t_resolution,
                              client_room
                              )
                if img_strs:
                    # Emit current chunk
                    if len(img_strs) > 1:
                        # Merge if many slices
                        img_str = merge_heatmap_slices(img_strs)
                    else:
                        img_str = img_strs[0]
                    # Put to image queue to be emitted from 'service_main'
                    generator_output_q.put({'img': img_str,
                                            'filename': filename,
                                            'viz_type': viz_type,
                                            'mz_range': [mz0, mz1],
                                            't_range': [t0_chunk, t1_chunk],
                                            't_resolution': t_resolution,
                                            'client_room': client_room,
                                            })
                # Start new chunk
                t0_chunk = t0_row
                img_strs = []
            # Continue collecting the same chunk
            t1_chunk = t1_row
            img_strs.append(img_str_row)
            
        if img_strs:
            # Emit chunk
            if len(img_strs) > 1:
                # Merge if many slices
                img_str = merge_heatmap_slices(img_strs)
            else:
                img_str = img_strs[0]
            # Put to image queue to be emitted from 'service_main'
            generator_output_q.put({'img': img_str,
                                    'filename': filename,
                                    'viz_type': viz_type,
                                    'mz_range': [mz0, mz1],
                                    't_range': [t0_chunk, t1_chunk],
                                    't_resolution': t_resolution,
                                    'client_room': client_room,
                                    })

        if (t0_chunk is None) or (t1 < t_range[1]):
            # (All) requested visualizations not available
            # Make request for the remaining time range
            viz_cache_put('requests',
                          filename,
                          viz_type,
                          [ t1_chunk or t_range[0], t_range[1] ],
                          mz_range,
                          t_resolution,
                          client_room
                          )
        # TODO: Emit data_request (if needed, avoid duplicate requests
        if filename not in signal_cache:
            self.log("Need to request data from FileIoService, not implemented")
        #     await self.emit_client_notification('data_request',
        #                                         {'filename': filename
        #                                          't_resolution': t_resolution
        #                                          }
        #                                         )

    async def on_stop_visualize_range(self, data):
        """ Stop visualization, if still running; use filename and ranges as input:
            - if none specified, stop all visualizations for the client;
            - with file name specified, stop the file visualization;
            - with ranges specified, stop visualizing current ranges;

        Parameters
        ----------
        data : dict(name, value, cookies, no_logging, no_data_logging...)
               value: JSON data from UI,
                      keys: 'filename', 't_range', 'mz_range';  or
                      keys: 'filename', 'ranges';
        """
        await self.emit_client_notification('stop_data_request',
                                            data['value'],
                                            **get_client_notification_args(data))
        d = deepcopy(data)
        ranges = d['value'].pop('ranges', None)
        if not ranges:
            # await kill_cache(data)
            return
        for r in ranges:
            d['value']['mz_range'] = r['mz_range']
            d['value']['t_range'] = r['t_range']
            # await kill_cache(d)

    async def on_tps_parameters_selected(self, data):
        """TPS parameters selected from the dropdown
        """
        await self.emit_client_notification('tps_data_request',
                                            data['value'],
                                            **get_client_notification_args(data)
                                            )

    # ---------------------------------

    # ========== FileService notifications ==========
    async def on_heatmap_image(self, data):
        value = data['value']
        await self.emit_client_notification(
                                'heatmap_figure_data',
                                value,
                                **{**get_client_notification_args(data),
                                   'room': data['client_room']
                                   }
                                )
    
    async def on_spec_trace_image(self, data):
        value = data['value']
        await self.emit_client_notification(
                        'spec_stack_figure_data',
                        value,
                        **{**get_client_notification_args(data),
                           'room': data['client_room']
                           }
                        )

    async def on_data_stream_coordinates(self, data):
        data.update({'acquisition': False})
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

    # ========== FileIoService notifications ==========
    async def on_acquisition_coordinates(self, data):
        global client
        global signal_cache

        value = data['value']
        
        filename = value.get('filename')
        self.log(filename)
        
        mz = np.frombuffer( value.get('mz'), dtype=np.float32 )
        signal_array = ExtendableDataArray(array_module=da)
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        signal_cache[filename] = signal_array

        # kwargs = get_client_notification_args(data)
        # if set_figure_ranges:
        #     # Set UI figure ranges
        #     await self.emit_client_notification(
        #                         'figure_ranges',
        #                         {'filename': filename,
        #                          'mz_range': mz_range,
        #                          't_range': t_range,
        #                          },
        #                         **{**kwargs,
        #                           'room': (data.get('client_room') or filename)
        #                           }
        #                         )

    async def on_acquired_spectrum(self, data):
        global signal_cache
        # Get package index
        value = data['value']
        i = value.get('i')
        self.log(i)
        filename = value.get('filename')

        ti = np.array( [value.get('t')], dtype=np.float32 )
        spec = np.frombuffer(value.get('spec'), dtype=np.float32)
        spec = spec.reshape(-1, 1)
        signal_array = signal_cache[filename]

        if 'mz' in value:
            # mz coordinates provided with data
            mz = np.frombuffer(value['mz'], dtype=np.float32)
            mz = mz.reshape(-1,)
        else:
            # Use mz coordinates from signal_array
            mz = signal_array.data_array.mz

        signal_array.extend_array(spec,
                                  [mz, ti],
                                  'time'
                                  )

        available_t_range = [signal_array.data_array.time[0].item(),
                             signal_array.data_array.time[-1].item()
                             ]
        viz_cache_process_requests(filename,
                                   available_t_range,
                                   )

    async def on_acquisition_finished(self, data):
        global signal_cache
        
        value = data['value']
        filename = value.get('filename')

        signal_array = signal_cache[filename]

        available_t_range = [signal_array.data_array.time[0].item(),
                             signal_array.data_array.time[-1].item()
                             ]
        viz_cache_process_requests(filename,
                                   available_t_range,
                                   )

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

        viz_cache_put(data, 'tps', visualizer)

        if set_tps_parameters:
            dropdown_items = [{'label': info,
                               'value': i
                               } for i, info in enumerate(tps_info)
                            ]
            kwargs = get_client_notification_args(data)
            await self.emit_client_notification(
                            'tps_parameters',
                            dropdown_items,
                            **kwargs
                            )

    async def on_acquired_tps_data(self, data):
        value = data['value']
        # speci = value.get('i')
        # self.log(speci)

        global tps_data

        global tps_visualizers
        visualizer = viz_cache_get(data, 'tps')
        if not visualizer:  # data request was cancelled
            return
        # Extend signal cache
        tps_data = np.frombuffer( value.get('data'), dtype=np.float32 )
        tps_data = tps_data.reshape(-1, 1)
        ti = value.get('t')
        td = np.array( [timedelta(seconds=ti)] ) # Convert to timedelta
        parameter = visualizer.data_array.parameter

        return #TODO: TPS visualizations not implemented

        await visualizer.extend_array(tps_data,
                                      [parameter, td],
                                      'time',
                                      )
        await visualizer.extend_visualizations(**get_client_notification_args(data))            
    # ----------------------------------------------


#         # Timeseries trace
#         x = list( arr_to_viz.time.values.astype(float) * 1e-9 )
#         y = list( arr_to_viz.sum('mz').values.astype(float) )
#         ts_trace = deepcopy(DEFAULT_TRACE)
#         ts_trace.update({'name': 'TIC [%.2f, %.2f]' %(mz0, mz1),
#                          'x': x,
#                          'y': y
#                          }
#                         )
#         timeseries_data = {'filename': self.filename,
#                            'traces': [ts_trace],
#                            'mz_range': mz_range,
#                            }
#         await client.emit_client_notification('timeseries_figure_data',
#                                        timeseries_data,
#                                        **{**kwargs,
#                                           'room': (kwargs.get('client_room') or timeseries_data.get('filename'))
#                                           }
#                                        )

class DataVizServiceClient(BaseServiceClient):
    async def init_service(self):
        global generator_input_q # TODO:
        global generator_output_q # TODO:

        generator_input_q = self.generator_input_q = Queue() # TODO:
        generator_output_q = self.generator_output_q = Queue() # TODO:
        self.generator_procs = []

        n_jobs = cpu_count()
        for i in range(n_jobs):
            self.log("ImageGenerator %s/%s" %(i+1, n_jobs))
            gen_proc = ImageGenerator(self.generator_input_q,
                                      self.generator_output_q
                                      )
            gen_proc.start()
            self.generator_procs.append(gen_proc)
            await self.sio.sleep(1)
            

    async def service_main(self):
        global visualizers
        
        while True:
            # Check queues for new images
            try:
                img_data = self.generator_output_q.get_nowait()
            except Empty:
                await self.sio.sleep(.1)
                continue

            # Got new image
            self.log("Image ready: ", img_data)
            # Put viz to cache
            viz_cache_put('visualizations',
                          img_data['filename'],
                          img_data['viz_type'],
                          img_data['t_range'],
                          img_data['mz_range'],
                          img_data['t_resolution'],
                          img_data['img']
                          )
            # Select endpoint based on viz_type
            viz_type = img_data.get('viz_type')
            # TODO: Emit all figures into common figure_data endpoint?
            if viz_type == 'spectrogram':
                endpoint = 'heatmap_figure_data'
            if viz_type == 'waterfall':
                endpoint = 'spec_stack_figure_data'
            # Emit figure data
            client_room = img_data['client_room']
            self.log("Emitting to: ", client_room)
            await self.emit_client_notification(
                            endpoint,
                            img_data,
                            room=client_room,
                            )
            # End of main loop
        # Exit
        # Terminate image generators
        [proc.terminate() for proc in self.generator_procs]
        await self.sio.disconnect()


def run():
    global client
    args = parse_cmd_args()
    client = DataVizServiceClient(args['url'],
                                  args['port'],
                                  (args['ns'], DataVizServiceNamespace)
                                  )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
