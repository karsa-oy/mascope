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

import asyncio
import json
import os
import numpy as np
import dask.array as da
import sqlite3

from copy import deepcopy
from datetime import datetime, timedelta
from multiprocessing import (
                        Queue,
                        Event,
                        cpu_count
                        )
from queue import Empty
from time import time

from karsalib import BaseClientNamespace, BaseServiceClient, CacheQueueConnector, \
                     parse_cmd_args, get_client_notification_args
from karsatof.kworker import ImageGenerator
from karsatof.kcollector import ExtendableDataArray
from karsatof.kimage import (
                    DEFAULT_TRACE,
                    convert_base64_to_img,
                    convert_to_base64,
                    hstack_imgs,
                    )
from karsatof.kutil import AttrDict

VIZ_TYPES_SUPPORTED = {'spectrogram', 'timeseries', 'waterfall'}

NO_DATA_LOGGING_DEAULT = False
client = None

# Cache for data arrays
cache = {}

generator_input_q = None
shutdown_event = None
generator_input_cache = None

# Cache for requests and visualizations
# in_memory_db = ':memory:'
# For debugging, write db into a file
test_db = datetime.now().strftime("DataViz_%Y%m%d_%Hh%Mm%Ss") + '.db'
con = sqlite3.connect(test_db) 
cur = con.cursor()

# Create requests table
cur.execute('''CREATE TABLE requests
               (filename text,
                viz_type text,
                t0 real,
                t1 real,
                mz0 real,
                mz1 real,
                t_resolution real,
                client_room text,
                request_id text)
            ''')

# ======= Visualization/request cache (db) methods =======
def viz_cache_get(table,
                  fields,
                  filename=None,
                  viz_type=None,
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
                '''.format(fields, table, query), # ORDER BY t0 ASC
                args
                )
    return cur


async def viz_cache_process_requests(filename):
    global REQUEST_PROCESSORS

    # Get all pending requests for filename
    request_data_rows = viz_cache_get(
                            'requests',
                            '''
                            viz_type,
                            t0, t1,
                            mz0, mz1,
                            t_resolution,
                            client_room,
                            request_id
                            ''',
                            filename,
                            )
    # Loop through db entries
    for row in request_data_rows:
        # print("[viz_cache_process_requests]: processing row: %s" %str(row))
        viz_type, t0, t1, mz0, mz1, t_resolution, client_room, request_id = row

        # Select processing method based on 'data_type' and process request
        processed_until = await REQUEST_PROCESSORS[viz_type](
                                    filename=filename,
                                    viz_type=viz_type,
                                    t0=t0,
                                    t1=t1,
                                    mz0=mz0,
                                    mz1=mz1,
                                    t_resolution=t_resolution,
                                    client_room=client_room,
                                    request_id=request_id,
                                    )

        if processed_until is False:
            # print("Request holds:", client_room, [t0, t1])
            continue

        if processed_until == t0:
            # print("Request holds:", client_room, [t0, t1])
            continue
        elif processed_until < t1:
            print("Update request:", client_room, [processed_until, t1])
            # Only part of request served, update request start time
            t0_new = processed_until
            viz_cache_update('requests',
                            ['t0'],
                            [t0_new],
                            filename,
                            viz_type,
                            [t0, t1],
                            [mz0, mz1],
                            t_resolution,
                            client_room,
                            request_id,
                            )
        else:
            print("Release request:", client_room, [t0, t1])
            # Request served fully, release from cache
            viz_cache_release('requests',
                              request_id=request_id,
                              viz_type=viz_type
                              )

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
    
    cur.execute('''INSERT INTO {} VALUES ({})
                '''.format(table, ','.join( ['?']*len(values) )),
                values
                )    
    con.commit()

def viz_cache_put_or_update_request(filename,
                                    viz_type,
                                    t_range,
                                    mz_range,
                                    t_resolution,
                                    client_room,
                                    request_id,
                                    ):
    global con
    # Get existing requests
    cur = viz_cache_get('requests',
                        'client_room',
                        filename,
                        viz_type,
                        t_range,
                        mz_range,
                        t_resolution
                        )
    dup_request = cur.fetchone()
    if dup_request:
        # Found a duplicate request, append new client room
        client_rooms = [client_room, *dup_request]
        client_rooms_str = "'" + ",".join(client_rooms) + "'"
        viz_cache_update('requests',
                         ['client_room'],
                         [client_rooms_str],
                         filename,
                         viz_type,
                         t_range,
                         mz_range,
                         t_resolution
                         )
        return
    else:
        # Make new request
        viz_cache_put('requests',
                      filename,
                      viz_type,
                      t_range,
                      mz_range,
                      t_resolution,
                      client_room,
                      request_id
                      )

def viz_cache_release(table,
                      request_id=None,
                      filename=None,
                      client_room=None,
                      viz_type=None,
                      t_range=None,
                      mz_range=None,
                      t_resolution=None,
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
        query = join_str.join([query, 'mz0 = ? AND mz1 = ?'])
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

    if request_id:
        args.append(request_id)
        query = join_str.join([query, 'request_id = ?'])
        join_str = ' AND '

    cur.execute('''UPDATE {} SET {} WHERE {}
                '''.format(table, set_query, query),
                args
                )
    con.commit()

async def process_visualization_request(filename,
                                  viz_type,
                                  t0,
                                  t1,
                                  mz0,
                                  mz1,
                                  t_resolution,
                                  client_room,
                                  request_id,
                                  ):
    """Routine for processing a visualization request

    Parameters
    ----------
    filename : [type]
        [description]
    viz_type : [type]
        [description]
    t0 : [type]
        [description]
    t1 : [type]
        [description]
    mz0 : [type]
        [description]
    mz1 : [type]
        [description]
    t_resolution : [type]
        [description]
    client_room : [type]
        [description]

    Returns
    -------
    float or bool
        Returns the time point until which the request was served,
        or False if no (enough) data was available.
    """

    async def feed_signal_to_visualize(t_range_to_process):
        nonlocal cache_item
        try:
            signal_slice = cache_item.signal.sel(time=slice(*t_range_to_process),
                                                 mz=slice(mz0, mz1)
                                                 )
            period_slice = cache_item.signal_period.sel(time=slice(*t_range_to_process)
                                                 )
        except AttributeError:
            print("[feed_signal_to_visualize]: Signal not in cache: %s" %filename)
            return False

        if 0 in signal_slice.shape:
            print("empty slice")
            return False

        processed_until = t_range_to_process[0]
        BATCH_SIZE = 10 # Number of spectra to process at once (TODO: make parameter)
        no_spectra = signal_slice.shape[1]
        no_batches = int( np.ceil(no_spectra / BATCH_SIZE) )

        if no_spectra < BATCH_SIZE:
            return processed_until

        if t_resolution:
            # TODO: resample
            raise NotImplementedError
        
        # Feed signal batches to generators
        for i in range(no_batches):
            # print("feeding batch %s/%s" %((i+1), no_batches))
            t0 = time()
            # Batch indices
            i0 = i * BATCH_SIZE
            i1 = min(i0 + BATCH_SIZE, no_spectra)
            # print("i0: %s, i1: %s" %(i0, i1))
            # Take a batch
            spec_array = signal_slice[:, i0:i1]
            period_array = period_slice[i0:i1]
            # print(spec_array)

            # is_nanrow = spec_array.isnull().all(axis=0).any()
            is_nanrow = np.isnan( np.sum(spec_array.values, axis=1) ).any()
            if is_nanrow:
                # Some mz-channel full of nan => spectra not yet loaded
                # print("spec_array.isnull.all(axis=1).any()")
                # print("is nan row")
                # print("took %.2f sec" %(time()-t0))
                break

            # y_range = [0, spec_array.max().compute().item()] # TODO: better scaling
            y_range = None

            t0_i = float( spec_array.time[0] )
            t1_i = float( spec_array.time[-1] ) + float( period_array[-1] )

            # Put batch to queue to be visualized
            generator_input_q.put({
                            'data': spec_array,
                            'filename': filename,
                            'viz_type': viz_type,
                            'mz_range': [mz0, mz1],
                            't_range': [t0_i, t1_i],
                            'y_range': y_range,
                            't_resolution': t_resolution,
                            'client_room': client_room,
                            'request_id': request_id,
                            'persist_in_cache': False,
                            })

            processed_until = t1_i
            # print("took %.2f sec" %(time()-t0))

            await asyncio.sleep(.01)

        return processed_until

    cache_item = cache.get(request_id)
    if not cache_item:
        print("No such cache item: %s" %request_id)
    processed_until = await feed_signal_to_visualize([t0, t1])
    return processed_until


REQUEST_PROCESSORS = {'spectrogram': process_visualization_request,
                      'timeseries': process_visualization_request,
                      'waterfall': process_visualization_request
                      }

def merge_heatmap_slices(img_strs):
    slice_images = []
    for img_str in img_strs:
        img = convert_base64_to_img(img_str)
        slice_images.append(img)
    full_img = hstack_imgs(slice_images)
    full_img_str = convert_to_base64(full_img)
    return full_img_str


def get_namespace(filename):
    return '/' + filename.split('_')[0]



class DataVizServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = [
            'loaded_coordinates',
            'loaded_data',
            'service_state',
            'stop_visualize_range',
            'visualize_range',
            ]

    # ========== UI requests ==========
    async def on_visualize_range(self, data):
        """Visualization request

        First check if requested visualizations are in cache already, and emit if there.
        Secondly, put requests into cache for missing requests.
        Then check if signal for requested filename is in data cache, request from FileIoService if not.
        If signal is in cache, process requests.

        Parameters
        ----------
        data : dict(name, value, cookies, no_logging, no_data_logging...)
               value: JSON data from UI, keys: 'filename', 't_range', 'mz_range', 'viz_type'
        """
        value = data['value']
        self.log(data)
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        filename = value['filename']
        mz_range = value.get('mz_range')
        t_range = value.get('t_range')
        t_resolution = value.get('t_resolution')
        viz_types = value['viz_types']
        request_id = value['request_id']

        # Check if data_request is needed
        if request_id not in cache:
            # File not in cache, add
            cache[request_id] = AttrDict({})

        cache_item = cache[request_id]

        if not mz_range:
            for viz_type in viz_types:
                # Request full-range images from FileIo directly to client
                await self.emit_client_notification('data_request',
                                                    {'filename': filename,
                                                    'data_type': viz_type,
                                                    'request_id': request_id,
                                                    },
                                                    client_room=client_room,
                                                    namespace=get_namespace(filename)
                                                    )
            return

        data_request_needed = True
        if 'signal' not in cache_item:
            # Signal not in cache, request coordinates and signal in mz_range
            # Add dummy item to avoid duplicate requests
            cache_item.signal = None
            # Request signal coordinates
            self.log("Request coordinates")
            await self.emit_client_notification('coordinate_request',
                                                {'request_id': request_id,
                                                 'filename': filename,
                                                 'data_type': 'signal',
                                                 'dims': ['mz'],
                                                 },
                                                namespace=get_namespace(filename)
                                                )
            # Request signal
            self.log("Request signal in range: %s" %str(mz_range))
            await self.emit_client_notification('data_request',
                                                {'filename': filename,
                                                 'data_type': 'signal',
                                                 'mz_range': mz_range,
                                                 'request_id': request_id,
                                                },
                                                namespace=get_namespace(filename)
                                                )
        elif cache_item.signal:
            cached_slice = cache_item.signal.sel(mz=slice(*mz_range),
                                                 )
            data_request_needed = True
            mz_range_missing = mz_range

            if cached_slice.mz.shape[0] > 0:
                # Requested range at least partly cached
                # print("cached_slice mz: [%.4f, %.4f]" %(cached_slice.mz[0].item(),
                #                                         cached_slice.mz[-1].item())
                #       )
                cached_mz_range = [cached_slice.mz[0].item(),
                                   cached_slice.mz[-1].item()
                                   ]
                mz_range_missing = [ cached_mz_range[1], cached_mz_range[0] ]
                data_request_needed = False
                min_dmz = 1e-2
                if (cached_mz_range[0] - mz_range[0]) > min_dmz:
                    # Data missing at the bottom of the range
                    data_request_needed = True
                    mz_range_missing[0] = mz_range[0]
                if (mz_range[1] - cached_mz_range[1]) > min_dmz:
                    # Data missing at the top of the range
                    data_request_needed = True
                    mz_range_missing[1] = mz_range[1]
                # print("mz_range_missing: [%.4f, %.4f]" %(mz_range_missing[0], mz_range_missing[1])
                #     )

            # Request signal
            if data_request_needed:
                self.log("Emit data request: %s" %mz_range_missing)
                await self.emit_client_notification('data_request',
                                                    {'filename': filename,
                                                    'data_type': 'signal',
                                                    'mz_range': mz_range_missing,
                                                    'request_id': request_id,
                                                    },
                                                    namespace=get_namespace(filename)
                                                    )
        # Add a request, or add to existing request
        for viz_type in viz_types:
            viz_cache_put_or_update_request(filename,
                                            viz_type,
                                            t_range,
                                            mz_range,
                                            t_resolution,
                                            client_room,
                                            request_id
                                            )
        if not data_request_needed:
            # Process request
            await viz_cache_process_requests(filename)


    async def on_stop_visualize_range(self, data):
        """Release visualization requests from cache

        Parameters
        ----------
        data : dict(name, value, cookies, no_logging, no_data_logging...)
               value: JSON data from UI,
                      keys: 'request_ids', list of request ids to release
        """
        global cache
        value = data['value']
        filename = value['filename']
        request_ids = value['request_ids']
        if not filename:
            return
        for request_id in request_ids:
            viz_cache_release('requests',
                              request_id=request_id,
                              )
            generator_input_cache.cache_delete_key(request_id)
            cache.pop(request_id)
        await self.emit_client_notification('stop_data_request',
                                            data['value'],
                                            **{**get_client_notification_args(data),
                                               'namespace': get_namespace(filename)})
    # ---------------------------------

    # ========== FileIoService notifications ==========

    async def on_loaded_coordinates(self, data):
            """
            """
            # print("on_loaded_coordinates")
            global cache

            value = data['value']
            
            request_id = value['request_id']
            filename = value['filename']
            data_type = value['data_type']
            coordinates = value['coordinates']

            # Initialize data array
            dims = coordinates.keys()
            for dim in dims:
                coordinate_values = []
                if len(coordinates[dim]):
                    coordinate_values = np.frombuffer( coordinates[dim], dtype=np.float32 )
                coordinates.update( {dim: coordinate_values} )
            
            data_array = ExtendableDataArray(array_module=np)
            data_array.init_array(dims=dims,
                                  coords=coordinates,
                                  name=data_type,
                                  )
            period_array = ExtendableDataArray(array_module=np)
            period_array.init_array(dims=('time'),
                                    coords=[[]],
                                    name='_'.join([data_type, 'period'])
                                    )
            # Put to data cache
            cache[request_id].update({data_array.name: data_array,
                                    period_array.name: period_array,
                                    })

    async def on_loaded_data(self, data):
        """Data loaded from FileIoService
        """

        async def on_loaded_signal(data):
            """TODO: This is duplicate with on_acquired_spectrum in FileIoPrivateNamespace
            """
            # print("on_loaded_signal")
            global cache

            value = data['value']
            # i = value.get('i')
            request_id = value['request_id']
            filename_base = value['filename']

            ti = np.array( [value['t']], dtype=np.float32 )
            period = np.array( [value['period']], dtype=np.float32 )
            # self.log(ti.item())
            spec = np.frombuffer(value['spec'], dtype=np.float32)
            spec = spec.reshape(-1, 1)

            # Get data arrays from cache
            signal_array = cache[request_id]['signal']
            period_array = cache[request_id]['signal_period']

            if 'mz' in value:
                # mz coordinates provided with data (Orbitrap)
                mz = np.frombuffer(value['mz'], dtype=np.float32)
                mz = mz.reshape(-1,)
            else:
                # Use mz coordinates from signal_array (TOF)
                mz = signal_array.mz

            if ((signal_array.time.shape[0] == 0) or
                (ti.item() > signal_array.time[-1])
                ):
                # self.log("extending time-wise")
                # Extend data arrays time-wise
                signal_array.extend_array(spec,
                                        [mz, ti],
                                        'time'
                                        )
                period_array.extend_array(period,
                                        [ti],
                                        'time'
                                        )
            elif ti.item() in signal_array.time:
                # self.log("extending mz-wise")
                # Extend data arrays mz-wise
                signal_array.combine_first(spec,
                                           [mz, ti]
                                           )
            
            await viz_cache_process_requests(filename_base)


        data_type = data['value']['data_type']
        # print("[on_loaded_data]: %s" %data_type)
        if data_type == 'signal':
            await on_loaded_signal(data)


    # async def on_tps_parameter_info(self, data):
    #     value = data['value']
    #     tps_info = value.get('tps_info')
    #     set_tps_parameters = value.get('set_tps_parameters', True)

    #     visualizer = TPSVisualizer()

    #     # Initialize visualizer cache
    #     visualizer.init_array(dims=('parameter', 'time'),
    #                           data=None,
    #                           coords=[tps_info, []],
    #                           name='tps'
    #                           )

    #     viz_cache_put(data, 'tps', visualizer)

    #     if set_tps_parameters:
    #         dropdown_items = [{'label': info,
    #                            'value': i
    #                            } for i, info in enumerate(tps_info)
    #                         ]
    #         kwargs = get_client_notification_args(data)
    #         await self.emit_client_notification(
    #                         'tps_parameters',
    #                         dropdown_items,
    #                         **kwargs
    #                         )

    # async def on_acquired_tps_data(self, data):
    #     value = data['value']
    #     # speci = value.get('i')
    #     # self.log(speci)

    #     global tps_data

    #     global tps_visualizers
    #     visualizer = viz_cache_get(data, 'tps')
    #     if not visualizer:  # data request was cancelled
    #         return
    #     # Extend signal cache
    #     tps_data = np.frombuffer( value.get('data'), dtype=np.float32 )
    #     tps_data = tps_data.reshape(-1, 1)
    #     ti = value.get('t')
    #     td = np.array( [timedelta(seconds=ti)] ) # Convert to timedelta
    #     parameter = visualizer.parameter

    #     return #TODO: TPS visualizations not implemented

    #     await visualizer.extend_array(tps_data,
    #                                   [parameter, td],
    #                                   'time',
    #                                   )           
    
    # ----------------------------------------------


class DataVizServiceClient(BaseServiceClient):
    async def init_service(self):
        global generator_input_q
        global shutdown_event
        global generator_input_cache

        generator_input_q = Queue()
        self.generator_input_q =  Queue()
        shutdown_event = Event()
        generator_input_cache = CacheQueueConnector('request_id/viz_type',
                                                    generator_input_q,
                                                    self.generator_input_q,
                                                    shutdown_event
                                                    )
        self.generator_output_q = Queue()
        self.generator_procs = []

        n_jobs = cpu_count()
        for i in range(n_jobs):
            self.log("ImageGenerator %s/%s" %(i+1, n_jobs))
            gen_proc = ImageGenerator(self.generator_input_q,
                                      self.generator_output_q,
                                      shutdown_event
                                      )
            gen_proc.start()
            self.generator_procs.append(gen_proc)
            await self.sio.sleep(1)
            

    async def service_main(self):
        # start input cache thread
        generator_input_cache.start()

        while True:
            # Check queues for new images
            try:
                img_data = self.generator_output_q.get_nowait()
            except Empty:
                await self.sio.sleep(.1)
                continue

            # Got new image
            # self.log("Image ready: ", img_data)
            put_to_cache = img_data.get('persist_in_cache')
            # if put_to_cache:
            # TODO: Obsolete, no visualizations table anymore
            #     # Put viz to cache
            #     # self.log("Put to cache: %s" %str(img_data))
            #     viz_cache_put('visualizations',
            #                 img_data['filename'],
            #                 img_data['viz_type'],
            #                 img_data['t_range'],
            #                 img_data['mz_range'],
            #                 img_data['t_resolution'],
            #                 img_data.get('img') or json.dumps(img_data.get('traces'))
            #                 )
            # Emit figure data
            client_room = img_data.pop('client_room')
            if client_room:
                client_rooms = client_room.split(',')
                for client_room in client_rooms:
                    await self.emit_client_notification(
                                    'figure_data',
                                    img_data,
                                    room=client_room,
                                    no_data_logging=True,
                                    )
            # End of main loop
        # Exit
        # Kill generator_input_cache thread
        shutdown_event.set()
        # Terminate image generators
        [proc.terminate() for proc in self.generator_procs]
        await self.sio.disconnect()


def run():
    global client
    global shutdown_event

    print("PID: %s" %os.getpid())

    args = parse_cmd_args()
    client = DataVizServiceClient(args['url'],
                                  args['port'],
                                  (args['ns'], DataVizServiceNamespace)
                                  )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        shutdown_event.set()

if __name__=='__main__':
    run()
