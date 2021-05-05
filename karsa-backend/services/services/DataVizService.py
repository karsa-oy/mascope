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
import numpy as np
import dask.array as da
import sqlite3

from copy import deepcopy
from datetime import datetime, timedelta
from multiprocessing import (
                        Queue,
                        cpu_count
                        )
from queue import Empty
from time import time

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
from karsatof.kutil import AttrDict

VIZ_TYPES_SUPPORTED = {'spectrogram', 'timeseries', 'waterfall'}

NO_DATA_LOGGING_DEAULT = False
client = None

# Cache for data arrays
cache = {}

generator_input_q = None # TODO:
generator_output_q = None # TODO:

# Cache for requests and visualizations
# in_memory_db = ':memory:'
# For debugging, write db into a file
test_db = datetime.now().strftime("DataViz_%Y%m%d_%Hh%Mm%Ss") + '.db'
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

# ======= Visualization/request cache (db) methods =======
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

    cur.execute('''SELECT {} FROM {} WHERE {}
                '''.format(fields, table, query), # ORDER BY t0 ASC
                args
                )
    return cur

def viz_cache_process_requests(filename):
    global REQUEST_PROCESSORS

    # Get all pending requests for filename
    request_data_rows = viz_cache_get(
                            'requests',
                            'viz_type, t0, t1, mz0, mz1, t_resolution, client_room',
                            filename,
                            )
    # Loop through db entries
    for row in request_data_rows:
        # print("[viz_cache_process_requests]: processing row: %s" %str(row))
        viz_type, t0, t1, mz0, mz1, t_resolution, client_room = row

        # Select processing method based on 'data_type' and process request
        processed_until = REQUEST_PROCESSORS[viz_type](
                                    filename=filename,
                                    viz_type=viz_type,
                                    t0=t0,
                                    t1=t1,
                                    mz0=mz0,
                                    mz1=mz1,
                                    t_resolution=t_resolution,
                                    client_room=client_room,
                                    )

        if not processed_until:
            # Nothing was processed
            continue
        
        if processed_until < t1:
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
                            )
        else:
            # Request served fully, release from cache
            viz_cache_release('requests',
                              filename,
                              client_room,
                              viz_type,
                              [t0, t1],
                              [mz0, mz1],
                              t_resolution
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
                                    client_room
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
                      client_room
                      )

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

def process_visualization_request(filename,
                                  viz_type,
                                  t0,
                                  t1,
                                  mz0,
                                  mz1,
                                  t_resolution,
                                  client_room
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

    global cache
    global generator_input_q # TODO: global q

    def feed_cached_visualizations(request_t_range):
        nonlocal cache_item

        t_range_to_process = request_t_range

        viz_array = cache_item.get(viz_type)
        if not viz_array:
            return request_t_range
        if viz_array.attrs.get('mz_range') != [mz0, mz1]:
            return request_t_range

        img_slice = viz_array.sel(time=slice(*request_t_range)).load()
        
        if len(img_slice) == 0:
            return request_t_range

        if t_resolution:
            # TODO: resample
            raise NotImplementedError
        
        # Filter nans
        not_nan = np.logical_not( img_slice.isnull() )
        img_slice = img_slice[not_nan]

        # Put to queue to be emitted from service_main
        for i, img_array in enumerate(img_slice):
            # Load image
            img_str = img_array.item()

            t0_i = float( img_array.time.item() )
            if i < len(img_slice) - 1:
                t1_i = float( img_slice[i+1].time.item() )
            else:
                t1_i = t0_i+1 # TODO:

            t_range_to_process[0] = t1_i
            # Put to image queue to be emitted from 'service_main'
            img_data = {'filename': filename,
                        'viz_type': viz_type,
                        'mz_range': [mz0, mz1],
                        't_range': [t0_i, t1_i],
                        't_resolution': t_resolution,
                        'client_room': client_room,
                        'persist_in_cache': False,
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
            generator_output_q.put(img_data)

        if t_range_to_process[0] == t_range_to_process[1]:
            t_range_to_process = False
        # print("t_range_to_process: %s" %str(t_range_to_process))
        return t_range_to_process
        # t_range_to_process = request_t_range

        # # Get already cached visualizations
        # img_data_rows = viz_cache_get('visualizations',
        #                               'viz, t0, t1, mz0, mz1, viz_type',
        #                               filename,
        #                               viz_type,
        #                               request_t_range,
        #                               [mz0, mz1],
        #                               t_resolution
        #                               )
        # # Loop through cached visualizations
        # for row in img_data_rows:
        #     viz_row, t0_row, t1_row, mz0_row, mz1_row, viz_type_row = row
        #     if viz_row is None:
        #         print("viz is None")
        #         continue
        #     t_range_to_process[0] = t1_row
        #     # Put to image queue to be emitted from 'service_main'
        #     img_data = {'filename': filename,
        #                 'viz_type': viz_type,
        #                 'mz_range': [mz0_row, mz1_row],
        #                 't_range': [t0_row, t1_row],
        #                 't_resolution': t_resolution,
        #                 'client_room': client_room,
        #                 'persist_in_cache': False,
        #                 }
        #     try:
        #         traces = json.loads(viz_row)
        #         img_data.update({'traces': traces})
        #     except json.JSONDecodeError:
        #         img_str = viz_row
        #         img_data.update({'img': img_str})
        #     generator_output_q.put(img_data)

        # if t_range_to_process[0] == t_range_to_process[1]:
        #     t_range_to_process = False
        # print("t_range_to_process: %s" %str(t_range_to_process))
        # return t_range_to_process

    def feed_signal_to_visualize(t_range_to_process):
        nonlocal cache_item
        try:
            signal_slice = cache_item.signal.sel(time=slice(*t_range_to_process),
                                                 mz=slice(mz0, mz1)
                                                 )
            period_slice = cache_item.signal_period.sel(time=slice(*t_range_to_process)
                                                 )
        except AttributeError:
            print("[feed_signal_to_visualize]: Signal not in cache: %s" %filename)
            return t_range_to_process[0]

        BATCH_SIZE = 10 # Number of spectra to process at once (TODO: make parameter)
        no_spectra = signal_slice.shape[1]
        no_batches = int( np.ceil(no_spectra / BATCH_SIZE) )

        if no_spectra < BATCH_SIZE:
            return False

        if t_resolution:
            # TODO: resample
            raise NotImplementedError
        
        y_range = [0, signal_slice.max().compute().item()] # TODO: better scaling

        # Feed signal batches to generators
        for i in range(no_batches):
            # Batch indices
            i0 = i * BATCH_SIZE
            i1 = min(i0 + BATCH_SIZE, no_spectra)
            # print("i0: %s, i1: %s" %(i0, i1))
            # Take a batch
            spec_array = signal_slice.transpose()[i0:i1].load()
            period_array = period_slice[i0:i1]
            # print("spec_array shape: %s" %str(spec_array.shape))

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
                            'persist_in_cache': True,
                            })

        processed_until = t1_i
        return processed_until


    cache_item = cache.get(filename)
    if not cache_item:
        print("No such cache item: %s" %filename)
    request_t_range = [t0, t1]
    t_range_to_process = feed_cached_visualizations(request_t_range)
    if t_range_to_process:
        processed_until = feed_signal_to_visualize(t_range_to_process)
    else:
        processed_until = t1
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

        global generator_output_q # TODO:

        value = data['value']
        # self.log(value)
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        filename = value['filename']
        mz_range = value['mz_range']
        t_range = value['t_range']
        t_resolution = value.get('t_resolution')
        viz_type = value['viz_type']

        # New TODO:

        # Check if data_request is needed
        if filename not in cache:
            # File not in cache, add
            cache[filename] = AttrDict({})

        cache_item = cache[filename]

        if viz_type not in cache_item:
            # Request full range images into cache
            # Initialize array
            viz_array = ExtendableDataArray(array_module=np,
                                            dtype=object,
                                            chunk_size=1,
                                            )
            viz_array.init_array(dims=('time',),
                                 coords=[[]],
                                 name=viz_type
                                 )
            # Put to cache
            cache_item[viz_type] = viz_array
            # Request full-range images from FileIo
            await self.emit_client_notification('data_request',
                                                {'filename': filename,
                                                 'data_type': viz_type,
                                                 },
                                                namespace=get_namespace(filename)
                                               )

        if 'signal' not in cache_item:
            # Add dummy item to avoid duplicate requests
            cache_item['signal'] = None
            # Request signal coordinates
            await self.emit_client_notification('coordinate_request',
                                                {'filename': filename,
                                                 'data_type': 'signal',
                                                 'dims': ['mz'],
                                                 },
                                                namespace=get_namespace(filename)
                                                )
            # Request signal
            await self.emit_client_notification('data_request',
                                                {'filename': filename,
                                                 'data_type': 'signal',
                                                },
                                                namespace=get_namespace(filename)
                                               )

        # Add a request, or add to existing request
        viz_cache_put_or_update_request(filename,
                                        viz_type,
                                        t_range,
                                        mz_range,
                                        t_resolution,
                                        client_room
                                        )
        # Process request
        viz_cache_process_requests(filename)

        # //New TODO:
        """
        # Get already cached visualizations
        img_data_rows = viz_cache_get('visualizations',
                                      'viz, t0, t1, mz0, mz1, viz_type',
                                      filename,
                                      viz_type,
                                      t_range,
                                      mz_range,
                                      t_resolution
                                      )
        # Emit cached visualizations and update request ranges accordingly
        vizs = []
        t0_chunk = None
        t1_chunk = None
        # Loop through cached visualizations
        for row in img_data_rows:
            viz_row, t0_row, t1_row, mz0_row, mz1_row, viz_type_row = row
            # print("t0_row: %s, t1_row: %s, mz0_row: %s, mz1_row: %s, viz_type: %s"
            #       %(t0_row, t1_row, mz0_row, mz1_row, viz_type_row)
            #       )
            # self.log("t0_chunk: %.2f, t1_chunk: %.2f" %(t0_chunk or 0, t1_chunk or 0))
            if t0_chunk is None:
                # Start new continuous chunk of images
                vizs = []
                t0_chunk = t0_row
                if t0_chunk > t_range[0]:
                    # Gap in the beginning
                    # self.log("Gap in the beginning: %.2f-%.2f" %(t_range[0], t0_chunk))
                    # Make request for the gap
                    viz_cache_put_or_update_request(filename,
                                                    viz_type,
                                                    [ t_range[0], t0_chunk ],
                                                    mz_range,
                                                    t_resolution,
                                                    client_room
                                                    )
            elif abs(t0_row - t1_chunk) > 1e-5: # t1 of previous slice != t0 of current one
                # Gap in the middle
                # self.log("Gap in the middle: %.2f-%.2f" %(t1_chunk, t0_row))
                # Make request for the gap
                viz_cache_put_or_update_request(filename,
                                                viz_type,
                                                [t1_chunk, t0_row], # From previous t1 until current t0
                                                mz_range,
                                                t_resolution,
                                                client_room
                                                )
                # Emit current chunk
                for viz in vizs:
                    # Put to visualization queue to be emitted from 'service_main'
                    img_data = {'filename': filename,
                                'viz_type': viz_type,
                                'mz_range': mz_range,
                                't_range': [t0_chunk, t1_chunk],
                                't_resolution': t_resolution,
                                'client_room': client_room,
                                'persist_in_cache': False,
                                }
                    try:
                        traces = json.loads(viz)
                        img_data.update({'traces': traces})
                    except json.JSONDecodeError:
                        img_str = viz
                        img_data.update({'img': img_str})
                    # self.log("Putting cached viz: %s" %str(img_data))
                    generator_output_q.put(img_data)
                # Start new chunk
                t0_chunk = t0_row
                vizs = []
            # Continue collecting the same chunk
            t1_chunk = t1_row
            vizs.append(viz_row)
            
        # Emit images fetched from cache
        for viz in vizs:
            # Put to image queue to be emitted from 'service_main'
            img_data = {'filename': filename,
                        'viz_type': viz_type,
                        'mz_range': mz_range,
                        't_range': [t0_chunk, t1_chunk],
                        't_resolution': t_resolution,
                        'client_room': client_room,
                        'persist_in_cache': False,
                        }
            try:
                traces = json.loads(viz)
                img_data.update({'traces': traces})
            except json.JSONDecodeError:
                img_str = viz
                img_data.update({'img': img_str})
            generator_output_q.put(img_data)

        if (t0_chunk is None) or (t1_chunk < t_range[1]):
            # (All) requested visualizations were not available
            # self.log("Gap in the end: %.2f-%.2f" %(t1_chunk or t_range[0], t_range[1]))
            # Make request for the remaining time range
            viz_cache_put_or_update_request(filename,
                                            viz_type,
                                            [ t1_chunk or t_range[0], t_range[1] ],
                                            mz_range,
                                            t_resolution,
                                            client_room
                                            )
        # Check if data_request is needed
        if filename not in cache:
            # File not in cache, add
            # Add dummy cache item to avoid duplicate data_requests
            cache[filename] = {}
            # Request full-range images
            await self.emit_client_notification('data_request',
                                                {'filename': filename,
                                                 'data_type': viz_type,
                                                 },
                                                namespace=get_namespace(filename)
                                               )
            # Request signal
            # await self.emit_client_notification('data_request',
            #                                     {'filename': filename,
            #                                      'data_type': 'signal',
            #                                     },
            #                                     namespace=get_namespace(filename)
            #                                    )

            return
        elif 'signal' in cache[filename]:
            # Signal array in cache
            signal_array = cache[filename].signal
            # self.log("Process request on existing signal array")
            # Check for available time range and process request
            try:
                available_t_range = [signal_array.time[0].item(),
                                     signal_array.time[-1].item()
                                     ]
            except Exception as e:
                # Nothing in the signal array yet
                print(e)
                return

            viz_cache_process_requests(filename)
        """

    async def on_stop_visualize_range(self, data):
        """Release visualization requests from cache

        Parameters
        ----------
        data : dict(name, value, cookies, no_logging, no_data_logging...)
               value: JSON data from UI,
                      keys: 'client_rooms', list of client rooms to release
        """
        value = data['value']
        client_rooms = value['client_rooms']
        for client_room in client_rooms:
            viz_cache_release('requests',
                              client_room=client_room,
                              )
        # await self.emit_client_notification('stop_data_request',
        #                                     data['value'],
        #                                     **get_client_notification_args(data))
    # ---------------------------------

    # ========== FileIoService notifications ==========

    async def on_loaded_coordinates(self, data):
            """
            """
            # print("on_loaded_coordinates")
            global cache

            value = data['value']
            
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
            
            data_array = ExtendableDataArray(array_module=da)
            data_array.init_array(dims=dims,
                                  coords=coordinates,
                                  name=data_type
                                  )
            period_array = ExtendableDataArray(array_module=np)
            period_array.init_array(dims=('time'),
                                    coords=[[]],
                                    name='_'.join([data_type, 'period'])
                                    )
            # Put to data cache
            cache[filename].update({data_array.name: data_array,
                                    period_array.name: period_array,
                                    })

    async def on_loaded_data(self, data):
        """Data loaded from FileIoService
        """
        async def on_loaded_image(data):
            # print("on_loaded_image")
            global generator_output_q
            value = data['value']
            filename = value['filename']
            viz_type = value['data_type']

            viz_array = cache[filename][viz_type]

            mz_range = value['mz_range']
            if 'mz_range' not in viz_array.attrs:
                viz_array.attrs.update({'mz_range': mz_range})
            if mz_range != viz_array.attrs['mz_range']:
                print("Loaded image mz_range mismatch!")

            ti = np.array([ value['t_range'][0] ], dtype=np.float32)
            img_str = value.get('img') or json.dumps(value.get('traces'))
            
            viz_array.extend_array(np.array([img_str]),
                                   [ti],
                                   'time'
                                   )
            viz_cache_process_requests(filename)
            return

        async def on_loaded_signal(data):
            """TODO: This is duplicate with on_acquired_spectrum in FileIoPrivateNamespace
            """
            # print("on_loaded_signal")
            global cache

            value = data['value']
            # i = value.get('i')
            filename_base = value['filename']

            ti = np.array( [value['t']], dtype=np.float32 )
            period = np.array( [value['period']], dtype=np.float32 )
            # self.log(ti.item())
            spec = np.frombuffer(value['spec'], dtype=np.float32)
            spec = spec.reshape(-1, 1)

            # Get data arrays from cache
            signal_array = cache[filename_base]['signal']
            period_array = cache[filename_base]['signal_period']

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
            
            viz_cache_process_requests(filename_base)

            return data['value'].get('i')

        data_type = data['value']['data_type']

        if data_type in VIZ_TYPES_SUPPORTED:
            return await on_loaded_image(data)
        if data_type == 'signal':
            return await on_loaded_signal(data)


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

        while True:
            # Check queues for new images
            try:
                img_data = self.generator_output_q.get_nowait()
            except Empty:
                await self.sio.sleep(.1)
                continue

            # Got new image
            # self.log("Image ready: ", img_data)
            put_to_cache = img_data.pop('persist_in_cache')
            if put_to_cache:
                # Put viz to cache
                # self.log("Put to cache: %s" %str(img_data))
                viz_cache_put('visualizations',
                            img_data['filename'],
                            img_data['viz_type'],
                            img_data['t_range'],
                            img_data['mz_range'],
                            img_data['t_resolution'],
                            img_data.get('img') or json.dumps(img_data.get('traces'))
                            )
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
