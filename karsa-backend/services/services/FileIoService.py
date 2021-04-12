# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization. It holds in memory
a :class:`~karsa_hw_interfaces.karsatof.kdatapool.KDataPool` instance
of the currently selected data path.
      
Created on Thu May  7 12:43:13 2020
"""

import os
import subprocess
import asyncio
import fnmatch
import json
import sqlite3
import xarray
import zarr
import numpy as np
import dask.array as da

from multiprocessing import Queue
from PIL import Image
from copy import deepcopy
from datetime import datetime
from queue import Empty


from karsalib import (BaseClientNamespace,
                      BridgeServiceClient,
                      Logger,
                      parse_cmd_args, 
                      get_client_notification_args
                      )
from karsatof.kcollector import ExtendableDataArray
from karsatof.kdatapool import parse_path_from_sample_name
from karsatof.kimage import (convert_base64_to_img, convert_to_base64)


client = None
cache = {}

signal_q = None # TODO:

in_memory_db = ':memory:'
test_db = datetime.now().strftime("FileIo_%Y%m%d_%Hh%Mm%Ss") + '.db'
con = sqlite3.connect(test_db) 
cur = con.cursor()
            
# Create requests table            
cur.execute('''CREATE TABLE requests
               (filename text,
                t0 real,
                t1 real,
                mz0 real,
                mz1 real,
                t_resolution real,
                client_room text)
            ''')

def cache_get(table,
              fields,
              filename=None,
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

def cache_process_requests(filename, t_range):
    global cache

    signal_array = cache[filename]['signal']
    period_array = cache[filename]['period']

    # Get all pending requests for filename
    request_data_rows = cache_get(
                            'requests',
                            't0, t1, mz0, mz1, t_resolution, client_room',
                            filename,
                            )

    for row in request_data_rows:
        print("[cache_process_requests]: processing row: %s" %str(row))
        t0, t1, mz0, mz1, t_resolution, client_room = row
        
        t0_row = max(t_range[0], t0)
        t1_row = min(t_range[1], t1)

        signal_slice = signal_array.data_array.sel(
                                        time=slice(t0_row, t1_row),
                                        mz=slice(mz0, mz1)
                                        )
        period_slice = period_array.data_array.sel(
                                        time=slice(t0_row, t1_row)
                                        )
        print("signal_slice shape: %s" %str(signal_slice.shape))

        if signal_slice.shape[1] == 0:
            continue

        if t_resolution:
            # TODO: resample
            raise NotImplementedError
        
        # Put to queue to be visualized
        global signal_q # TODO: global q
        y_range = [0, signal_slice.max().compute().item()] # TODO: better scaling

        for i, spec_array in enumerate(signal_slice.transpose()):
            ti = float( spec_array.time.item() )
            period = float( period_array.data_array[i] )
            signal_q.put({
                        'filename': filename,
                        'spec': spec_array.values.astype(np.float32).tobytes(),
                        't': ti,
                        'period': period,
                        'client_room': client_room,
                        })

        if (ti + period) < t1:
            # Only part of request served, update request time range
            t0_new = ti + period
            cache_update('requests',
                            ['t0'],
                            [t0_new],
                            filename,
                            [t0, t1],
                            [mz0, mz1],
                            t_resolution,
                            client_room,
                          
                            )
        else:
            # Request served fully, release rom cache
            cache_release('requests',
                              filename,
                              client_room,
                              [t0, t1],
                              [mz0, mz1],
                              t_resolution
                              )

def cache_put(table,
                  filename,
                  t_range,
                  mz_range,
                  t_resolution,
                  *args
                  ):
    
    global con
    cur = con.cursor()
    
    values = (filename,
              t_range[0],
              t_range[1],
              mz_range[0],
              mz_range[1],
              t_resolution,
              *args
              )
    
    cur.execute('''INSERT INTO {} VALUES (?,?,?,?,?,?,?)
                '''.format(table),
                values
                )    
    con.commit()

def cache_release(table,
                  filename=None,
                  client_room=None,
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

def cache_update(table,
                 fields,
                 values,
                 filename=None,
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


class FileIoPublicNamespace(BaseClientNamespace):
    endpoints = [
        # DataViz
        'figure_data',
        # //
        ]

    async def on_figure_data(self, data):
        self.log(data)
        value = data['value']
        filename = value['filename']
        viz_type = value['viz_type']
        image_array = cache[filename][viz_type]
        
        ti = np.array([ value['t_range'][0] ], dtype=np.float32)
        img_str = value['img']
        image_array.extend_array(np.array([img_str]),
                                 [ti],
                                 'time'
                                 )

    # async def on_image_to_save(self, data):
    #     value = data['value']
    #     filename = value['filename']
    #     img_filename = value['img_filename']
    #     img_str = value['img']
    #     sample_data_path = parse_path_from_sample_name(filename)
    #     img_path = os.path.join(sample_data_path, img_filename)
    #     img = convert_base64_to_img(img_str)
    #     img.save(img_path)


class FileIoPrivateNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    endpoints = [
        # TOFService
        'acquisition_coordinates',
        'acquired_spectrum',
        # 'acquired_tps_data',
        'acquisition_finished',
        # 'tps_parameter_info',
        # //
        # SampleManager
        'mz_coordinate_request',
        'signal_request',
        'stop_data_request',
        'tps_data_request',
        # //
        # Router
        'service_state',
        # //
        ]

    service_state = dict()

    # ========== TOFService requests ==========
    async def on_acquisition_coordinates(self, data):
        """Initialize acquisition cache with received coordinates

        Parameters
        ----------
        data : dict
            keys: 'mz' and 'time'
        """
        global cache

        value = data['value']
        filename_base = value.get('filename')
        print("Start acquiring sample: %s" %filename_base)
        
        mz = np.frombuffer( value['mz'], dtype=np.float32 )
        t_range = value['t_range']

        filename_signal = base_to_zarr_filename(filename_base, 'signal')
        signal_array = ExtendableDataArray(path=filename_signal,
                                           array_module=da
                                           )
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        filename_period = base_to_zarr_filename(filename_base, 'period')
        period_array = ExtendableDataArray(path=filename_period,
                                           array_module=np
                                           )
        period_array.init_array(dims=('time'),
                                coords=[[]],
                                name='period'
                                )
        # Write attributes
        attributes = {'id': filename_base,
                      'length': float(t_range[1]),
                      'range': [ float(mz[0]), float(mz[-1]) ],
                      }
        attr_path = os.path.join(
                        parse_path_from_sample_name(filename_base),
                        '.attrs'
                        )
        with open(attr_path, 'w') as f:
            json.dump(attributes, f, indent=4)

        # Initialize visualization arrays
        filename_spectrogram = base_to_zarr_filename(filename_base, 'spectrogram')
        spectrogram_array = ExtendableDataArray(path=filename_spectrogram,
                                                array_module=np,
                                                dtype=object,
                                                chunk_size=10,
                                                )
        spectrogram_array.init_array(dims=('time',),
                                     coords=[[]],
                                     name='spectrogram'
                                     )
        # Put to cache
        cache_item = {'signal': signal_array,
                      'period': period_array,
                      'spectrogram': spectrogram_array,
                      'attrs': attributes,
                      }
        cache[filename_base] = cache_item
        print("cache: %s" %str(cache))
        # Request visualizations from DataViz
        await self.emit_client_notification('visualize_range',
                                            {'filename': filename_base,
                                             'viz_type': 'spectrogram',
                                             't_range': [0, t_range[1]],
                                             'mz_range': [ float(mz[0]), float(mz[-1]) ],
        #                                      't_resolution': interval,
                                             },
                                            client_room='figure_data',
                                            namespace='/'
                                            )

    async def on_acquired_spectrum(self, data):
        """Receive new spectrum, add to cache

        Parameters
        ----------
        data : dict
            keys: 'filename', 'i', 't' and 'spec'
        """
        global cache
        # Get package index
        value = data['value']
        # i = value.get('i')
        filename_base = value['filename']

        ti = np.array( [value['t']], dtype=np.float32 )
        period = np.array( [value['period']], dtype=np.float32 )
        self.log(ti.item())
        spec = np.frombuffer(value['spec'], dtype=np.float32)
        spec = spec.reshape(-1, 1)
        signal_array = cache[filename_base]['signal']
        period_array = cache[filename_base]['period']

        if 'mz' in value:
            # mz coordinates provided with data (Orbitrap)
            mz = np.frombuffer(value['mz'], dtype=np.float32)
            mz = mz.reshape(-1,)
        else:
            # Use mz coordinates from signal_array (TOF)
            mz = signal_array.data_array.mz

        signal_array.extend_array(spec,
                                  [mz, ti],
                                  'time'
                                  )
        period_array.extend_array(period,
                                  [ti],
                                  'time'
                                  )
        
        available_t_range = [signal_array.data_array.time[0].item(),
                             signal_array.data_array.time[-1].item() + period.item()
                             ]
        cache_process_requests(filename_base, available_t_range)

        return data['value']['i']

    async def on_acquired_tps_data(self, data):
        value = data['value']
        filename_base = value.get('filename')
        ti = np.array( [value.get('t')], dtype=np.float32 )
        tps_data = np.frombuffer( value.get('data'), dtype=np.float32)
        tps_data = tps_data.reshape(-1, 1)
        tps_array, _ = cache_get(data, 'tps')
        if tps_array:   # TODO: tps_array is None on killing acquisition from MainUI
            tps_info = tps_array.data_array.parameter
            tps_array.extend_array(tps_data,
                                   [tps_info, ti],
                                   'time'
                                   )

    async def on_acquisition_finished(self, data):
        global cache
        value = data['value']
        filename_base = value.get('filename')
        filename = base_to_zarr_filename(filename_base, 'signal')
        print("Finished acquiring file: %s" %filename)
        signal_array = cache[filename_base]['signal']
        # tps_array, _ = cache_get(data, 'tps')
        # cache_release(data)
        if signal_array:
            signal_array.flush()  # TODO: signal_array is None on killing acquisition from MainUI
        else:
            Warning("[on_acquistion_finished]: signal_array is None")
        # if tps_array:
        #     tps_array.flush()      # TODO: tps_array is None on killing acquisition from MainUI
        # else:
        #     Warning("[on_acquistion_finished]: tps_array is None")
        
        # Repeat the notification into root ns for DataViz
        # await self.emit_client_notification('acquisition_finished',
        #                                      value,
        #                                      namespace='/'
        #                                      )

    async def on_tps_parameter_info(self, data):
        value = data['value']
        filename_base = value.get('filename')
        filename = base_to_zarr_filename(filename_base, 'tps')

        print("Writing TPS data into: %s" %filename)

        tps_info = value.get('tps_info')
        
        tps_array = ExtendableDataArray(path=filename,
                                        array_module=da
                                        )
        tps_array.init_array(dims=('parameter', 'time'),
                             coords=[tps_info, []],
                             name='tps'
                             )
        cache_put(data, 'tps', tps_array)
    # -----------------------------------------
    # =========== DataViz requests ===========
    async def on_mz_coordinate_request(self, data):
        value = data['value']

        filename = value['filename']
        mz_range = value.get('mz_range', None)
        
        if filename not in cache:
            # File not in cache, load and put
            filename_signal = base_to_zarr_filename(filename, 'signal')
            signal_array = open_mfzarr(filename_signal)
            filename_period = base_to_zarr_filename(filename, 'period')
            period_array = open_mfzarr(filename_period)
            attr_path = os.path.join(
                        parse_path_from_sample_name(filename),
                        '.attrs'
                        )
            with open(attr_path, 'w') as f:
                attributes = json.load(f)

            cache[filename] = {'signal': signal_array,
                               'period': period_array,
                               'attrs': attributes,
                               }

        signal_array = cache[filename]['signal']            

        if mz_range is None:
            mz0 = float( signal_array.data_array.mz[0] )
            mz1 = float( signal_array.data_array.mz[-1] )
            mz_range = [mz0, mz1]

        mz = signal_array.data_array.mz.sel(mz=slice(*mz_range))
        mz = mz.values.astype(np.float32)

        await self.emit_client_notification(
                            'mz_coordinates',
                            {'filename': filename,
                             'mz': mz.tobytes(),
                             'mz_range': mz_range,
                             },
                            namespace='/',
                            no_data_logging=True
                            )

    async def on_signal_request(self, data):
        self.log(data)

        value = data['value']

        filename = value['filename']
        client_room = value.get('client_room') or data['cookies']['src_sid'][0]
        mz_range = value.get('mz_range', None)
        t_range = value.get('t_range', None)
        
        signal_array = cache[filename]['signal']
        period_array = cache[filename]['period']
        attributes = cache[filename]['attrs']

        if mz_range is None:
            mz_range = attributes['range']
            
        if t_range is None:
            t_range = [0, attributes['length']]

        # Put request to cache
        print("Making request: filename: %s, t_range: %s, mz_range: %s, client_room: %s"
              %(filename, t_range, mz_range, client_room)
              )
        cache_put('requests',
                      filename,
                      t_range,
                      mz_range,
                      None, # t_resolution,
                      client_room
                      )
        available_t_range = [signal_array.data_array.time[0],
                             signal_array.data_array.time[-1] + period_array.data_array[-1].item()
                             ]
        cache_process_requests(filename, available_t_range)

    async def on_data_request(self, data):
        # print("Data request:", data)
        value = data['value']
        kwargs = get_client_notification_args(data)

        filename = value['filename']
        mz_range = value.get('mz_range', None)
        t_range = value.get('t_range', None)
        
        signal_array, signal_env = cache_get(data, 'signal')
        if not signal_array:
            # File not in cache, load and put
            filename_zarr = base_to_zarr_filename(filename, 'signal')
            signal_array = open_mfzarr(filename_zarr)
            cache_put(data, 'signal', signal_array)
            signal_array, signal_env = cache_get(data, 'signal')
        if isinstance(signal_array, ExtendableDataArray):
            signal_array = signal_array.data_array.to_dataset()

        if mz_range is None:
            mz0 = float( signal_array.mz[0] )
            mz1 = float( signal_array.mz[-1] )
            mz_range = [mz0, mz1]
            set_figure_ranges = True
        if t_range is None:
             # In case of incomplete acquisition, set to full_t_range
            t_range, _ = cache_get(data, 'full_t_range')
            if not t_range:
                t0 = float( signal_array.time[0] )
                t1 = float( signal_array.time[-1] )
                t_range = [t0, t1]

        signal = signal_array.signal.sel(
                    mz=slice(*mz_range),
                    time=slice(*t_range)
                    )
        if signal.shape[1] == 0:
            print("No data available in the requested time range!")
            return
        mz = signal.mz.values.astype(np.float32)
        t = signal.time.values.astype(np.float32)
        y_range = [0, signal.max().compute().item()]

        await self.emit_client_notification(
                            'data_stream_coordinates',
                            {'filename': filename,
                             'mz': mz.tobytes(),
                            #  'time': t.tobytes(),
                             'mz_range': mz_range,
                             't_range': t_range,
                             'y_range': y_range
                             },
                            set_figure_ranges=set_figure_ranges,
                            **{**kwargs,
                               'namespace': '/',
                               'no_data_logging': True
                               }
                            )
        
        stream_data = True
        # if set_figure_ranges:
        #     # Full range request, try to load images from file and send to DataViz
        #     try:
        #         heatmap_img = load_heatmap_image(filename)
        #         spec_imgs = load_spec_trace_images(filename)
        #         await self.emit_client_notification('heatmap_image',
        #                                             {'filename': filename,
        #                                              'mz_range': mz_range,
        #                                              't_range': t_range,
        #                                              'img': heatmap_img
        #                                              },
        #                                             **{**kwargs,
        #                                                    'namespace': '/',
        #                                                    'no_data_logging': True
        #                                                    }
        #                                                 )
        #         for t0, spec_img in spec_imgs:
        #             await self.emit_client_notification('spec_trace_image',
        #                                                 {'filename': filename,
        #                                                  'mz_range': mz_range,
        #                                                  't_range': [t0, t0], # t1 does not matter
        #                                                  'img': spec_img
        #                                                  },
        #                                                 **{**kwargs,
        #                                                    'namespace': '/',
        #                                                    'no_data_logging': True
        #                                                    }
        #                                                 )
        #         # No need to send data to DataViz
        #         stream_data = False
        #     except Exception as e:
        #         print(e)

        def stop_task():
            cache_release(data, 'signal')
            self.log(f"{data['name']} was cancelled due to a timeout.")
        TASK_TTL = 1200     # 2 min

        if stream_data:
            signal_env['speci'] = 0
            ttl_count = 0
            for i, spec_array in enumerate(signal.transpose()):
                if not cache_contains(data, 'signal'):
                    # Request has been cancelled
                    break
                ttl_count = 0
                while i - signal_env['speci'] > 10: # TODO: sync with spectra bundle size
                    ttl_count += 1
                    if ttl_count > TASK_TTL:
                        stop_task()
                        break
                    await asyncio.sleep(.1)
                spec = spec_array.values
                ti = float( spec_array.time )
                await self.emit_client_notification(
                                            'loaded_spectrum',
                                            {'filename': filename,
                                             'i': i,
                                             'spec': spec.tobytes(),
                                             'mz_range': mz_range,
                                             't_range': t_range,
                                             't': ti,
                                             },
                                            callback="speci_callback",
                                            callback_context=cache_get_keys(data),
                                            **{**kwargs,
                                               'namespace': '/',
                                               'no_data_logging': True
                                               }
                                            )
            # wait till last series of notifications (mod 10 in size) is processed by subscriber
            while i > signal_env['speci'] and ttl_count < TASK_TTL:
                await asyncio.sleep(.1)
        # cache_release(data, 'signal')     # TODO: is it needed here?
        await self.emit_client_notification('data_stream_finished',
                                            {'filename': filename,
                                             'mz_range': mz_range,
                                             't_range': t_range,
                                             },
                                            **{**kwargs, 'namespace': '/'}
                                            )
    def speci_callback(self, ctx, n):
        _, signal_env = cache_get(ctx, 'signal')
        if not signal_env is None:
            signal_env['speci'] = n

    async def on_stop_data_request(self, data):
        ranges = data['value'].pop('ranges', [])
        for r in ranges:
            data['value'].update({'mz_range': r['mz_range']})
            data['value'].update({'t_range': r['t_range']})
            await kill_cache(data)
            return
        await kill_cache(data)

    async def on_tps_data_request(self, data):        
        value = data['value']
        figure_ranges = value.pop('figure_ranges', {})
        filename = figure_ranges.get('filename', None)
        if filename is None:
            raise ValueError("Received data_request without filename")
        
        selected = value.get('tps_parameters_selected', None)
        if selected is None:
            return   
        parameters = [ v.get('label') for _, v in selected.items() ]

        sample_array, tps_env = cache_get(data, 'tps')
        if not sample_array:
            filename = base_to_zarr_filename(filename, '_tps')
            sample_array = open_mfzarr(filename)
            cache_put(data, 'tps', sample_array)
            sample_array, tps_env = cache_get(data, 'tps')

        t_range = figure_ranges.get('t_range', None)
        if t_range is None:
            t0 = float( sample_array.time[0] )
            t1 = float( sample_array.time[-1] )
            t_range = [t0, t1]
            
        tps_data = sample_array.data_array.loc[
                                    parameters,
                                    t_range[0]:t_range[1],
                                    ]
        t = tps_data.time.values.astype(np.float32)
        kwargs = get_client_notification_args(data)
        await self.emit_client_notification(
                            'tps_data_stream_coordinates',
                            {'filename': filename,
                             'parameters': parameters,
                            #  'time': t.tobytes(),
                             'set_tps_parameters': False,
                             },
                            **kwargs
                            )

        def stop_task():
            cache_release(data, 'tps')
            self.log(f"{data['name']} was cancelled due to a timeout.")
        TASK_TTL = 1200     # 2 min

        tps_env['tps_speci'] = 0
        ttl_count = 0
        for i, param_array in enumerate(tps_data.transpose()):
            if not cache_contains(data, 'tps'):
                # Request has been cancelled
                break
            ttl_count = 0
            while i - tps_env['tps_speci'] > 10:    # TODO: sync with spectra bundle size
                ttl_count += 1
                if ttl_count > TASK_TTL:
                    stop_task()
                    break
                await asyncio.sleep(.1)
            param_ys = param_array.values
            ti = float( param_array.time )
            await self.emit_client_notification('loaded_tps_data',
                                           {'filename': filename,
                                            'i': i,
                                            'tps_data': param_ys.tobytes(),
                                            't': ti,
                                            },
                                           callback="tps_speci_callback",
                                           callback_context=cache_get_keys(data),
                                           **kwargs
                                           )
        # wait till last series of notifications (mod 10 in size) is processed by subscriber
        while i > tps_env['tps_speci'] and ttl_count < TASK_TTL:
            await asyncio.sleep(.1)
        # cache_release(data, 'tps')     # TODO: is it needed here?
        await self.emit_client_notification('tps_data_stream_finished',
                                       {'filename': filename},
                                       **kwargs
                                       )
    def tps_speci_callback(self, ctx, n):
        _, tps_env = cache_get(ctx, 'tps')
        if not tps_env is None:
            tps_env['tps_speci'] = n
    # ----------------------------------------



# ========= File I/O functions =========
def base_to_zarr_filename(base_filename, variable):
    sample_data_path = parse_path_from_sample_name(base_filename)
    zarr_filename = variable + os.extsep + 'zarr'
    return os.path.join(sample_data_path, zarr_filename)

def load_heatmap_image(base_filename):
    sample_data_path = parse_path_from_sample_name(base_filename)
    heatmap_filename = 'heatmap.png'
    heatmap_file = os.path.join(sample_data_path, heatmap_filename)
    img = Image.open(heatmap_file)
    img_str = convert_to_base64(img)
    return img_str

def load_spec_trace_images(base_filename):
    sample_data_path = parse_path_from_sample_name(base_filename)
    all_files = next( os.walk(sample_data_path) )[2]
    imgs = []
    for spec_filename in fnmatch.filter(all_files, 'spec*.png'):
        spec_file = os.path.join(sample_data_path, spec_filename)
        img = Image.open(spec_file)
        img_str = convert_to_base64(img)
        t0 = float( spec_file.split('spec')[1].split('.png')[0] )
        imgs.append( (t0, img_str) )
    return imgs

def open_mfzarr(path, mode='r', concat_dim='time'):    
    if not os.path.exists(path):
        raise ValueError("Zarr file %s does not exist" %path)
    z = zarr.open(path, mode=mode)
    groups = [ g[0] for g in z.groups() ]
    x = xarray.concat([ xarray.open_zarr(path, g) for g in groups ],
                      concat_dim
                      )
    x.attrs = z.attrs.asdict()
    return x
    
def read_zarr_attributes(filepath):
    if not os.path.exists(filepath):
        raise ValueError("Zarr file %s does not exist" %filepath)
    z = zarr.open(filepath, mode='r')
    attributes = z.attrs.asdict()
    return attributes

def write_zarr_attributes(filepath, attributes):
    if not os.path.exists(filepath):
        raise ValueError("Zarr file %s does not exist" %filepath)
    z = zarr.open(filepath, mode='a')
    z.attrs.update(attributes)
# ---------------------------------------


class FileIoClient(BridgeServiceClient):
    
    async def init_service(self):
        global signal_q # TODO:

        signal_q = self.signal_q = Queue() # TODO:    

    async def service_main(self):
        global signal_q
        while True:
            # Check queue for signal to emit
            try:
                signal_data = self.signal_q.get_nowait()
            except Empty:
                await self.sio.sleep(.1)
                continue
            # Emit figure data
            client_room = signal_data.pop('client_room')
            self.log("Emitting t=%s to: " %signal_data['t'], client_room)
            await self.emit_public_notification(
                            'loaded_spectrum',
                            signal_data,
                            room=client_room,
                            )
            # End of main loop
        # Exit
        await self.sio.disconnect()

def run():
    args = parse_cmd_args()
    # FileIo should always be in private namespace with data producer
    if args['ns'] == '/':
        print("FileIoService must be in a private namespace. " +
              "Please restart the service with --ns option."
              )
        return

    client = FileIoClient(args['url'],
                          args['port'],
                          ('/', FileIoPublicNamespace),
                          (args['ns'], FileIoPrivateNamespace)
                          )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
