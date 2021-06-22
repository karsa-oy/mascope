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
import time
import subprocess
import asyncio
import fnmatch
import json
import sqlite3
import xarray
import zarr
import numpy as np
import dask.array as da

from multiprocessing import Queue, Event
from PIL import Image
from copy import deepcopy
from datetime import datetime
from queue import Empty


from karsalib import (BaseClientNamespace,
                      BridgeServiceClient,
                      LRUDict,
                      CacheQ,
                      Logger,
                      parse_cmd_args, 
                      get_client_notification_args,
                      t_mark
                      )
from karsatof.kcollector import ExtendableDataArray
from karsatof.kdatapool import parse_path_from_sample_name
from karsatof.kimage import (convert_base64_to_img, convert_to_base64)
from karsatof.kutil import AttrDict, generate_unique_key
from services.DataVizService import VIZ_TYPES_SUPPORTED



DATA_VERSION_NUMBER = '0.01'



client = None

# Cache for data arrays
cache = LRUDict(10)

service_q = None

# Cache for requests
# in_memory_db = ':memory:'
# For debugging, write db into a file
test_db = datetime.now().strftime("FileIo_%Y%m%d_%Hh%Mm%Ss") + '.db'
con = sqlite3.connect(test_db) 
cur = con.cursor()
# Create requests table            
cur.execute('''CREATE TABLE requests
               (filename text,
                data_type text,
                t0 real,
                t1 real,
                mz0 real,
                mz1 real,
                t_resolution real,
                client_room text,
                request_id text)
            ''')

# ======= Request cache (db) methods =======
def cache_get(table,
              fields,
              filename=None,
              data_type=None,
              t_range=None,
              mz_range=None,
              t_resolution=None,
              client_room=None,
              request_id=None,
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

    if data_type:
        args.append(data_type)
        query = join_str.join([query, 'data_type = ?'])
        join_str = ' AND '
        
    if t_range:
        args.extend(t_range)
        query = join_str.join([query, 't0 >= ? AND t1 <= ?'])
        join_str = ' AND '
        
    if mz_range:
        args.extend(mz_range)
        query = join_str.join([query, 'mz0 = ? AND mz1 = ?'])
        join_str = ' AND '
        
    if t_resolution:
        args.append(t_resolution)
        query = join_str.join([query, 't_resolution = ?'])
        join_str = ' AND '

    if client_room:
        args.append(client_room)
        query = join_str.join([query, 'client_room = ?'])
        join_str = ' AND '

    if request_id:
        args.append(request_id)
        query = join_str.join([query, 'request_id = ?'])
        join_str = ' AND '

    cur.execute('''SELECT {} FROM {} WHERE {}
                   ORDER BY t0 ASC
                '''.format(fields, table, query),
                args
                )
    return cur


def cache_process_requests(filename, flush=False, **kwargs):
    global REQUEST_PROCESSORS
    # Get all pending requests for filename
    t_data = {}
    t_mark(t_data, 'cache_process_requests:cache_get')
    request_data_rows = cache_get(
                            'requests',
                            '''
                            data_type,
                            t0, t1,
                            mz0, mz1,
                            t_resolution,
                            client_room,
                            request_id
                            ''',
                            filename,
                            **kwargs
                            )
    # Loop through db entries
    for row in request_data_rows:
        # print("[cache_process_requests]: processing row: %s" %str(row))
        data_type, t0, t1, mz0, mz1, t_resolution, client_room, request_id = row

        # Select processing method based on data_type and process request
        t_mark(t_data, f"cache_process_requests:{REQUEST_PROCESSORS[data_type].__name__}")
        processed_t_range = REQUEST_PROCESSORS[data_type](
                                    filename=filename,
                                    data_type=data_type,
                                    t0=t0,
                                    t1=t1,
                                    mz0=mz0,
                                    mz1=mz1,
                                    t_resolution=t_resolution,
                                    client_room=client_room,
                                    request_id=request_id,
                                    flush=flush
                                    )
        if not flush and not processed_t_range:
            # Nothing was processed
            t_mark(t_data, f"cache_process_requests:cache_row_skipped")
            continue
        
        if not flush and processed_t_range[1] < t1:
            # Only part of request served, update request start time
            t_mark(t_data, "cache_process_requests:cache_row_update")
            t0_new = processed_t_range[1]
            cache_update('requests',
                         ['t0'],
                         [t0_new],
                         filename,
                         data_type,
                         [t0, t1],
                         [mz0, mz1],
                         t_resolution,
                         client_room,
                         request_id,
                         )
        else:
            # Request served fully, release from cache
            t_mark(t_data, "cache_process_requests:cache_row_release")
            cache_release('requests',
                          request_id
                          )

        t_mark(t_data, "cache_process_requests:cache_row_done")


def cache_put(table,
              filename,
              data_type,
              t_range,
              mz_range,
              t_resolution,
              *args
              ):
    
    global con
    cur = con.cursor()
    
    values = (filename,
              data_type,
              t_range[0],
              t_range[1],
              mz_range[0],
              mz_range[1],
              t_resolution,
              *args
              )
    
    cur.execute('''INSERT INTO {} VALUES ({})
                '''.format(table, ','.join( ['?']*len(values) )),
                values
                )    
    con.commit()

def cache_release(table,
                  request_id=None,
                  filename=None,
                  client_room=None,
                  data_type=None,
                  t_range=None,
                  mz_range=None,
                  t_resolution=None
                  ):
        
    global con
    cur = con.cursor()
    
    args = []
    query = ''
    join_str = ''
    
    if request_id:
        args.append(request_id)
        query = join_str.join([query, 'request_id = ?'])
        join_str = ' AND '

    if filename:
        args.append(filename)
        query = join_str.join([query, 'filename = ?'])
        join_str = ' AND '
        
    if client_room:
        args.append(client_room)
        query = join_str.join([query, 'client_room = ?'])
        join_str = ' AND '

    if data_type:
        args.append(data_type)
        query = join_str.join([query, 'data_type = ?'])
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
                 data_type=None,
                 t_range=None,
                 mz_range=None,
                 t_resolution=None,
                 client_room=None,
                 request_id=None,
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

    if data_type:
        args.append(data_type)
        query = join_str.join([query, 'data_type = ?'])
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

    if request_id:
        args.append(request_id)
        query = join_str.join([query, 'request_id = ?'])
        join_str = ' AND '


    cur.execute('''UPDATE {} SET {} WHERE {}
                '''.format(table, set_query, query),
                args
                )
    con.commit()

def process_signal_request(filename,
                           data_type,
                           t0,
                           t1,
                           mz0,
                           mz1,
                           t_resolution,
                           client_room,
                           request_id,
                           flush=False
                           ):
    global cache

    if data_type != 'signal':
        raise ValueError("Wrong request processor selected!")

    cache_item = cache[filename]
    
    signal_slice = cache_item.signal.sel(time=slice(t0, t1),
                                         mz=slice(mz0, mz1)
                                         )
    period_slice = cache_item.signal_period.sel(time=slice(t0, t1)
                                                )

    if signal_slice.shape[1] == 0:
        return False

    if t_resolution:
        # TODO: resample
        raise NotImplementedError

    y_max = signal_slice.max().compute().item()
    
    # Put signal to queue to be emitted from service_main
    for i, spec_array in enumerate(signal_slice.transpose()):
        ti = float( spec_array.time.item() )
        period = float( period_slice[i] )
        data_item = {
                'data_type': data_type,
                'filename': filename,
                'spec': spec_array.values.astype(np.float32).tobytes(),
                't': ti,
                'period': period,
                'y_max': y_max,
                'client_room': client_room,
                'request_id': request_id,
                }
        if (mz0 is not None) or (mz1 is not None):
            mz = spec_array.mz.values
            data_item.update({'mz': mz.astype(np.float32).tobytes()
                              })
        service_q.cache_put(data_item)
    processed_t_range = (signal_slice.time[0], ti+period)
    if flush:
        termination_package = {
            'data_type': 'etx',
            'filename': filename,
            'client_room': client_room,
            'request_id': request_id,
            }
        print("Put termination package to queue")
        service_q.cache_put(termination_package)

    return processed_t_range

def process_image_request(filename,
                          data_type,
                          t0,
                          t1,
                          mz0,
                          mz1,
                          t_resolution,
                          client_room,
                          request_id,
                          flush=False
                          ):
    global cache

    cache_item = cache[filename]
    
    try:
        img_slice = cache_item[data_type].sel(time=slice(t0, t1)).load()
        period_slice = cache_item[data_type+'_period'].sel(time=slice(t0, t1)).load()
    except KeyError:
        print("Requested data_type: %s not cached. cache_item.keys: %s" % (data_type, list(cache_item.keys())) )
        return False

    processed_t_range = False
    if len(img_slice) == 0:
        return processed_t_range

    if t_resolution:
        # TODO: resample
        raise NotImplementedError
    
    # Filter nans
    not_nan = np.logical_not( img_slice.isnull() )
    img_slice = img_slice[not_nan]
    period_slice = period_slice[not_nan]

    # Put to queue to be emitted from service_main
    for i, img_array in enumerate(img_slice):
        img_str = img_array.item()

        t0_i = float( img_array.time.item() )
        t1_i = t0_i + float( period_slice[i].item() )

        img_data = {'filename': filename,
                    'viz_type': data_type,
                    'mz_range': [mz0, mz1],
                    't_range': [t0_i, t1_i],
                    'client_room': client_room,
                    'request_id': request_id,
                    }
        if img_str.startswith('data:image/png;base64'):
            # base64 png
            img_data.update({'img': img_str})
        else:
            # trace
            try:
                traces = json.loads(img_str)
                img_data.update({'traces': traces})
            except json.JSONDecodeError:
                print("Erroneous img_blob: %s" %img_str)
                continue
        service_q.cache_put(img_data)
        processed_t_range = (img_slice.time[0], t1_i)
    return processed_t_range


REQUEST_PROCESSORS = {'signal': process_signal_request,
                      'spectrogram': process_image_request,
                      'timeseries': process_image_request,
                      'waterfall': process_image_request,
                      }
# ------------------------------------------

class FileIoPublicNamespace(BaseClientNamespace):
    endpoints = []
    endpoints_room_sid = [
        # DataViz
        'figure_data',
        # //
        ]
    endpoints_room_instrument = []

    async def subscribe(self):
        if self.endpoints:
            await super().subscribe(self.endpoints)
        if self.endpoints_room_sid:
            await super().subscribe(self.endpoints_room_sid, self.room_sid)
        if self.endpoints_room_instrument:
            await super().subscribe(self.endpoints_room_instrument, self.room_instrument)

    async def on_figure_data(self, data):
        await self.parent.private_ns.on_figure_data(data)


class FileIoPrivateNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    endpoints = [
        # TOFControl
        'instrument_log_entry',
        'instrument_log_request',
        # //
        # TOFService
        'acquisition_started',
        'acquisition_coordinates',
        'acquired_spectrum',
        # 'acquired_tps_data',
        'acquisition_finished',
        # 'tps_parameter_info',
        # //
        # SampleManager
        'stop_data_request',
        'tps_data_request',
        # //
        # Router
        'service_state',
        # //
        # DataViz
        # 'figure_data',            # masked by public endpoint
        # Services
        'coordinate_request',
        'data_request',
        # //
        ]

    service_state = dict()

    # ========== TOFControl requests ==========
    async def on_instrument_log_entry(self, data):
        value = data['value']
        entry = value
        append_instrument_log(self.namespace.strip('/'), entry)
    
    async def on_instrument_log_request(self, data):
        value = data['value']
        client_room = data['cookies']['src_sid'][0]
        log = read_instrument_log(self.namespace.strip('/'))
        await self.emit_client_notification('instrument_log',
                                            log,
                                            room=client_room
                                            )
    # -----------------------------------------

    # ========== TOFService requests ==========
    async def on_acquisition_started(self, data):
        global cache

        filename = data['value']['filename']
        # Initialize visualization arrays in file cache and emit request to DataViz
        for viz_type in VIZ_TYPES_SUPPORTED:
            # Initialize array
            filename_viz = base_to_zarr_filename(filename, viz_type)
            viz_array = ExtendableDataArray(path=filename_viz,
                                            array_module=np,
                                            dtype=object,
                                            chunk_size=1,
                                            )
            viz_array.init_array(dims=('time',),
                                 coords=[[]],
                                 name=viz_type
                                 )
            viz_period = viz_type + '_period'
            filename_viz_period = base_to_zarr_filename(filename, viz_period)
            viz_period_array = ExtendableDataArray(path=filename_viz_period,
                                                   array_module=np,
                                                   dtype=object,
                                                   chunk_size=1,
                                                   )
            viz_period_array.init_array(dims=('time',),
                                        coords=[[]],
                                        name=viz_period
                                        )
            # Put to file cache
            cache[filename].update({viz_type: viz_array,
                                    viz_period: viz_period_array
                                    })
        # Request full-size visualization from DataViz
        await self.parent.emit_public_notification(
                'visualize_range',
                {'filename': filename,
                 'mz_range': data['value']['mz_range'],
                 't_range': data['value']['t_range'],
                 'viz_types': list(VIZ_TYPES_SUPPORTED),
                 'request_id': generate_unique_key(),
                 },
                client_room=self.parent.public_ns.room_sid,
                )

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

        if os.path.exists(filename_signal):
            # Should hit here only when trying to import a file which has already been imported/acquired
            print("File %s exists already! Canceling import" %filename_base)
            await self.emit_client_notification('stop_raw_import', {})
            return

        signal_array = ExtendableDataArray(path=filename_signal,
                                           array_module=da
                                           )
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        filename_period = base_to_zarr_filename(filename_base, 'signal_period')
        period_array = ExtendableDataArray(path=filename_period,
                                           array_module=np
                                           )
        period_array.init_array(dims=('time'),
                                coords=[[]],
                                name='signal_period'
                                )
        # Collect attributes
        attributes = {'filename': filename_base,
                      'length': float(t_range[1]),
                      'range': [ float(mz[0]), float(mz[-1]) ],
                      'data_version': DATA_VERSION_NUMBER
                      }
        # Write attributes
        attr_path = os.path.join(
                        parse_path_from_sample_name(filename_base),
                        '.attrs'
                        )
        with open(attr_path, 'w') as f:
            json.dump(attributes, f, indent=4)

        # Put to cache
        cache_item_dict = {'signal': signal_array,
                           'signal_period': period_array,
                           'attrs': attributes,
                           }
        cache_item = AttrDict(cache_item_dict)
        cache[filename_base] = cache_item
        print("cache: %s" %str(cache))

    async def on_acquired_spectrum(self, data):
        """Receive new spectrum, add to cache

        Parameters
        ----------
        data : dict
            keys: 'filename', 'i', 't', 'spec', 'period', ('mz')
        """
        global cache

        value = data['value']
        filename_base = value['filename']

        ti = np.array( [value['t']], dtype=np.float32 )
        period = np.array( [value['period']], dtype=np.float32 )
        print(ti.item())
        spec = np.frombuffer(value['spec'], dtype=np.float32)
        spec = spec.reshape(-1, 1)

        # Get data arrays from cache
        signal_array = cache[filename_base].signal
        period_array = cache[filename_base].signal_period

        if 'mz' in value:
            # mz coordinates provided with data (Orbitrap)
            mz = np.frombuffer(value['mz'], dtype=np.float32)
            mz = mz.reshape(-1,)
        else:
            # Use mz coordinates from signal_array (TOF)
            mz = signal_array.mz

        # Extend data arrays (write to file)
        signal_array.extend_array(spec,
                                  [mz, ti],
                                  'time'
                                  )
        period_array.extend_array(period,
                                  [ti],
                                  'time'
                                  )
        cache_process_requests(filename_base)
        return data['cnt']

    async def on_acquired_tps_data(self, data):
        value = data['value']
        filename_base = value.get('filename')
        # ti = np.array( [value.get('t')], dtype=np.float32 )
        # tps_data = np.frombuffer( value.get('data'), dtype=np.float32)
        # tps_data = tps_data.reshape(-1, 1)
        # tps_array, _ = cache_get(data, 'tps')
        # if tps_array:   # TODO: tps_array is None on killing acquisition from MainUI
        #     tps_info = tps_array.parameter
        #     tps_array.extend_array(tps_data,
        #                            [tps_info, ti],
        #                            'time'
        #                            )

    async def on_acquisition_finished(self, data):
        global cache
        value = data['value']
        filename_base = value['filename']
        cache_item = cache[filename_base]
        print("Finished acquiring file: %s" %filename_base)
        
        final_length = float(cache_item.signal.time[-1] +
                             cache_item.signal_period[-1]
                             )

        # Update attributes
        attributes = cache_item['attrs']
        attributes.update({'length': final_length
                           })
        # Write attributes
        attr_path = os.path.join(
                        parse_path_from_sample_name(filename_base),
                        '.attrs'
                        )
        with open(attr_path, 'w') as f:
            json.dump(attributes, f, indent=4)

        arrays_to_flush = ['signal', 'signal_period']
        for key in arrays_to_flush:
            # Flush arrays
            array = cache_item.get(key)
            if isinstance(array, ExtendableDataArray):
                print("Flush %s array" %key)
                array.flush()

        cache_process_requests(filename_base, data_type='signal', flush=True)
        # cache_release('requests', filename=filename_base, data_type='signal')

    async def on_tps_parameter_info(self, data):
        value = data['value']
        filename_base = value.get('filename')
        filename = base_to_zarr_filename(filename_base, 'tps')

        print("Writing TPS data into: %s" %filename)

        tps_info = value.get('tps_info')
        
        # tps_array = ExtendableDataArray(path=filename,
        #                                 array_module=da
        #                                 )
        # tps_array.init_array(dims=('parameter', 'time'),
        #                      coords=[tps_info, []],
        #                      name='tps'
        #                      )
        # cache_put(data, 'tps', tps_array)
    # -----------------------------------------

    # =========== DataViz requests ===========
    async def on_coordinate_request(self, data):
        global cache

        value = data['value']
        t_mark(value)

        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        filename = value['filename']
        data_type = value['data_type']

        if filename not in cache:
            # File not in cache, load and put
            file_dataset = load_file(filename)
            cache[filename] = file_dataset
            t_mark(value)

        file_cache_item = cache[filename]
        data_item = file_cache_item[data_type]

        coordinates = {}
        coordinate_data = {**value,
                           'coordinates': coordinates,
                           }

        requested_dims = value['dims']
        all_dims = data_item.dims
        for dim in all_dims:
            coord_values_b = []
            if dim in requested_dims:
                coord_values = data_item[dim].values
                coord_values_b = coord_values.astype(np.float32).tobytes()
            coordinates.update({dim: coord_values_b})

        t_mark(coordinate_data)
        await self.parent.emit_public_notification('loaded_coordinates',
                                                   coordinate_data,
                                                   room=client_room,
                                                   )

    async def on_data_request(self, data):
        global cache
        # self.log(data)
        value = data['value']
        t_mark(value)

        filename = value['filename']
        data_type = value['data_type']
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        request_id = value['request_id']
        mz_range = value.get('mz_range', None)
        t_range = value.get('t_range', None)
        
        if filename not in cache:
            # File not in cache, load and put
            t_mark(value, 'on_data_request:load_file')
            file_dataset = load_file(filename)
            cache[filename] = file_dataset

        file_cache_item = cache[filename]

        if mz_range is None:
            # Full mz range
            mz_range = file_cache_item.attrs['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, file_cache_item.attrs['length']]

        # Put request to cache
        t_mark(value, 'on_data_request:cache_put')
        cache_put('requests',
                  filename,
                  data_type,
                  t_range,
                  mz_range,
                  None, # t_resolution,
                  client_room,
                  request_id,
                  )
        # Process request(s)
        t_mark(value, 'on_data_request:cache_process_requests')
        cache_process_requests(filename)
        t_mark(value, 'on_data_request:out')

    async def on_figure_data(self, data):
        # self.log(data)
        value = data['value']
        t_mark(value)

        filename = value['filename']
        viz_type = value['viz_type']
        
        ti = np.array([ value['t_range'][0] ], dtype=np.float32)
        img_str = value.get('img') or json.dumps(value.get('traces'))
        img_period = value['t_range'][1] - value['t_range'][0]

        viz_array = cache[filename][viz_type]
        period_array = cache[filename][ (viz_type + '_period') ]
        viz_array.extend_array(np.array([img_str]),
                               [ti],
                               'time'
                               )
        period_array.extend_array(np.array( [img_period], dtype=np.float32 ),
                                  [ti],
                                  'time'
                                  )
        t_mark(value)

    async def on_stop_data_request(self, data):
        self.log(data)
        value = data['value']
        request_ids = value['request_ids']
        for request_id in request_ids:
            cache_release('requests', request_id=request_id)
            service_q.cache_delete_key(request_id)
        t_mark(value)

    async def on_tps_data_request(self, data):     
        # TODO: Deprecated, need to update   
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
            
        tps_data = sample_array.loc[
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
def append_instrument_log(log_path, new_entry):
    log_file = os.path.join(log_path, '.log')
    if not os.path.exists(log_file):
        # Log file does not yet exist, create
        with open(log_file, 'w') as f:
            json.dump([new_entry], f, indent=4)
    else:
        # Append log
        with open(log_file, 'r+') as f:
            instrument_log = json.load(f)
            instrument_log.append(new_entry)
            f.seek(0)
            json.dump(instrument_log, f, indent=4)

def read_instrument_log(log_path):
    log_file = os.path.join(log_path, '.log')
    try:
        with open(log_file, 'r+') as f:
            instrument_log = json.load(f)
    except FileNotFoundError:
        instrument_log = []
    return instrument_log

def base_to_zarr_filename(base_filename, variable):
    sample_data_path = parse_path_from_sample_name(base_filename)
    zarr_filename = variable + os.extsep + 'zarr'
    return os.path.join(sample_data_path, zarr_filename)

def get_file_data_vars(filepath):
    file_dirs = next(os.walk(filepath))[1]
    zarrs = []
    for var in fnmatch.filter(file_dirs, '*.zarr'):
        zarrs.append(var)
    return zarrs

def load_file(base_filename):
    """Load all stored variables in a file into a xarray.Dataset object

    Parameters
    ----------
    base_filename : str
        Base filename

    Returns
    -------
    xarray.Dataset
        Loaded data
    """
    print("Loading file: %s" %base_filename)
    filepath = parse_path_from_sample_name(base_filename)
    # Get all saved variable names
    zarrs = get_file_data_vars(filepath)
    # Load data from file
    dss = []
    for var in zarrs:
        var_path = os.path.join(filepath, var)
        try:
            var_ds = open_mfzarr(var_path)
            dss.append(var_ds)
        except ValueError as e:
            print("ValueError: Error reading %s, %s" %(var_path, e))
            continue
    # Merge into xarray.Dataset
    dataset = xarray.merge(dss)
    # Load attributes
    attr_path = os.path.join(filepath,
                            '.attrs'
                            )
    with open(attr_path, 'r') as f:
        attributes = json.load(f)
    # Attach to dataset
    dataset.attrs = attributes
    return dataset

def open_mfzarr(path, mode='r', concat_dim='time'):
    """Load data from a multi-file zarr into a xarray.Dataset

    Parameters
    ----------
    path : str
        zarr file path
    mode : str, optional
        File mode, by default 'r'
    concat_dim : str, optional
        Dimension name along which to concatenate the files,
        by default 'time'

    Returns
    -------
    xarray.Dataset
        Concatenated data

    Raises
    ------
    ValueError
        In case requested file does not exist
    """

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
        global service_q
        service_q = CacheQ('request_id/data_type/viz_type')


    async def service_main(self):
        MAX_RESPONSE_TIME = 15          # seconds to wait for the client response, then drop

        def public_ns_data_count(cnt):
            # the callback is triggered in the notification namespace
            self.public_ns.cnt = max(cnt, self.public_ns.cnt)
            self.public_ns.cnt_timestamp = time.time()

        self.public_ns.public_ns_data_count = public_ns_data_count
        self.public_ns.cnt = 0
        self.public_ns.cnt_timestamp = time.time()
        cnt = 0

        while True:
            # Check queue for signal to emit (put in cache_process_requests)
            try:
                data = service_q.cache_get()
                if not data:
                    await self.sio.sleep(.1)
                    continue
                while cnt - self.public_ns.cnt > 4:
                    if time.time() - self.public_ns.cnt_timestamp > MAX_RESPONSE_TIME:
                        # stop waiting frozen packages, if no response in due time
                        public_ns_data_count(cnt)
                        break
                    await self.sio.sleep(.1)
            except Empty:
                await self.sio.sleep(.1)
                continue
            except KeyboardInterrupt:
                break

            client_room = data.pop('client_room')
            cnt += 1
            await self.emit_public_notification(
                            'loaded_data',
                            data,
                            room=client_room,
                            callback='public_ns_data_count',
                            cnt=cnt
                            )
            # End of main loop
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
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        pass


if __name__=='__main__':
    run()
