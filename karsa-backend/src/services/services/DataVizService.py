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

from datetime import datetime, timedelta
from multiprocessing import (
                        Queue,
                        Event,
                        cpu_count
                        )
from queue import Empty
from time import time

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.struct import AttrDict, CacheQ
from karsalib.util import (generate_unique_key,
                           get_client_notification_args,
                           parse_cmd_args
                           )
from karsalib.logging import this_func_name, t_mark

from karsalib.struct import ExtendableDataArray
from karsaimg import VIZ_TYPES_SUPPORTED
from karsaimg.image import (
                    convert_base64_to_img,
                    convert_to_base64,
                    DEFAULT_TRACE,
                    hstack_imgs,
                    ImageGenerator
                    )

from services.FileIoService import filename_to_zarr_path, load_file


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
                request_id text,
                persist_in_cache integer)
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
                  persist_in_cache=None,
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

    if persist_in_cache:
        args.append(persist_in_cache)
        query = join_str.join([query, 'persist_in_cache = ?'])
        join_str = ' AND '

    cur.execute('''SELECT {} FROM {} WHERE {}
                '''.format(fields, table, query), # ORDER BY t0 ASC
                args
                )
    return cur


def viz_cache_pop(table,
                  fields,
                  filename=None,
                  viz_type=None,
                  t_range=None,
                  mz_range=None,
                  t_resolution=None,
                  client_room=None,
                  request_id=None,
                  persist_in_cache=None,
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

    # if t_range:
    #     args.extend(t_range)
    #     query = join_str.join([query, 't0 >= ? AND t1 <= ?'])
    #     join_str = ' AND '

    if t_range:
        # args.extend(t_range)
        if t_range[0]:
            args.append(t_range[0])
            query = join_str.join([query, 't0 >= ?'])
            join_str = ' AND '
        if t_range[1]:
            args.append(t_range[1])
            query = join_str.join([query, 't1 <= ?'])
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

    if persist_in_cache:
        args.append(persist_in_cache)
        query = join_str.join([query, 'persist_in_cache = ?'])
        join_str = ' AND '

    cur.execute('''SELECT rowid, {} FROM {} WHERE {}
                '''.format(fields, table, query),
                args
                )
    data = []
    for id, *d in cur.fetchall():
        data.append(d)
        cur.execute('''DELETE FROM {} WHERE rowid={}
                    '''.format(table, id)
                    )
    return data


def viz_cache_process_requests(filename, flush=False, **kwargs):
    global REQUEST_PROCESSORS
    global cache

    requests_to_release = []
    rows = viz_cache_pop(
                    'requests',
                    '''
                    request_id,
                    filename,
                    viz_type,
                    t0, t1,
                    mz0, mz1,
                    t_resolution,
                    client_room,
                    persist_in_cache
                    ''',
                    filename=filename,
                    **kwargs
                    )
    for row in rows:
        # print("[viz_cache_process_requests]: processing row: %s" %str(row))
        (request_id,
         filename,
         viz_type,
         t0,
         t1,
         mz0,
         mz1,
         t_resolution,
         client_room,
         persist_in_cache
         ) = row

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
                                    request_id=request_id,
                                    persist_in_cache=persist_in_cache,
                                    flush=flush
                                    )

        # some error/no data yet/no full data -- put (updated) request back
        # if processed_until is False or processed_until<t1:
        if processed_until != t1 and not flush:
            # print("Request holds or updated:", client_room, [t0, t1])
            viz_cache_put(filename,
                          viz_type,
                          [processed_until, t1],
                          [mz0, mz1],
                          t_resolution,
                          client_room,
                          request_id,
                          persist_in_cache
                          )
        # else:
        #     requests_to_release.append(request_id)
    if requests_to_release:
        # check requests_to_release are processed completely (for all viz_types) and release
        for id in set(requests_to_release):
            cur = viz_cache_get('requests', 'request_id', request_id=id)
            if not cur.fetchone():
                release_request(id)
        # acquired samples are cached under filename key - check to release
        cur = viz_cache_get('requests', 'request_id', filename=filename)
        # if not cur.fetchone() and filename in cache:
        #     del cache[filename]


def viz_cache_put(filename,
                  viz_type,
                  t_range,
                  mz_range,
                  t_resolution,
                  client_room,
                  request_id,
                  persist_in_cache=False
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
              client_room,
              request_id,
              persist_in_cache
              )
    
    cur.execute('''INSERT INTO {} VALUES ({})
                '''.format('requests', ','.join( ['?']*len(values) )),
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
                                    persist_in_cache=False
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
        viz_cache_put(filename,
                      viz_type,
                      t_range,
                      mz_range,
                      t_resolution,
                      client_room,
                      request_id,
                      persist_in_cache,
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

def process_visualization_request(filename,
                                  viz_type,
                                  t0,
                                  t1,
                                  mz0,
                                  mz1,
                                  t_resolution,
                                  client_room,
                                  request_id,
                                  persist_in_cache,
                                  flush
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

    def feed_ready_images():
        nonlocal cache_item
        viz_type_period = viz_type + '_period'
        try:
            img_slice = cache_item[viz_type].sel(time=slice(t0, t1)).load()
            period_slice = cache_item[viz_type_period].sel(time=slice(t0, t1)).load()
        except KeyError as e:
            print("Error in process_image_request: %s" %e)
            print("Requested data_type: %s not cached. cache_item.keys: %s" % (viz_type, list(cache_item.keys())) )
            return False

        processed_until = False
        if len(img_slice) == 0:
            return processed_until

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
                        'viz_type': viz_type,
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
            processed_until = t1_i
            client.generator_output_q.put(img_data)
        return processed_until

    def feed_signal_to_visualize(t_range_to_process):
        nonlocal cache_item

        processed_until = t0

        try:
            img_slice = cache_item[viz_type].sel(time=slice(t0, t1)).load()
        except KeyError as e:
            print("KeyError in feed_ready_images: %s: %s" %(viz_type, str(e)))
            return processed_until
        viz_type_period = viz_type + '_period'
        try:
            period_slice = cache_item[viz_type_period].sel(time=slice(t0, t1)).load()
        except KeyError as e:
            print("KeyError in feed_ready_images: %s %s" %(viz_type_period, str(e)))
            return processed_until

        if len(img_slice) == 0:
            return processed_until

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
                        'viz_type': viz_type,
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
            processed_until = t1_i
            # print("Feed ready images until: %s" %processed_until)
            client.generator_output_q.put(img_data)
        return processed_until

    def feed_signal_to_visualize(t_range_to_process):
        nonlocal cache_item

        signal_slice = cache_item.signal.sel(time=slice(*t_range_to_process),
                                                mz=slice(mz0, mz1)
                                                )
        period_slice = cache_item.signal_period.sel(time=slice(*t_range_to_process)
                                                )

        processed_until = t_range_to_process[0]

        if 0 in signal_slice.shape:
            print("empty slice")
            return processed_until
            
        BATCH_SIZE = 10 # Number of spectra to process at once (TODO: make parameter)
        no_spectra = signal_slice.shape[1]
        no_batches = int( np.floor(no_spectra / BATCH_SIZE) )
        if flush:
            no_batches = int( np.ceil(no_spectra / BATCH_SIZE) )

        if not no_batches:
            return processed_until

        if t_resolution:
            # TODO: resample
            raise NotImplementedError
        
        # signal_slice.load()
        # period_slice.load()

        # Feed signal batches to generators
        for i in range(no_batches):
            # print("feeding batch %s/%s" %((i+1), no_batches))
            t0 = time()
            # Batch indices
            i0 = i * BATCH_SIZE
            i1 = min(i0 + BATCH_SIZE, no_spectra)
            # print("i0: %s, i1: %s" %(i0, i1))
            # Take a batch
            spec_array = signal_slice[:, i0:i1].load()
            period_array = period_slice[i0:i1].load()
            # print(spec_array)

            # is_nanrow = spec_array.isnull().all(axis=0).any()
            # is_nanrow = np.isnan( np.sum(spec_array.values, axis=1) ).any()
            # if is_nanrow:
                # Some mz-channel full of nan => spectra not yet loaded
                # print("spec_array.isnull.all(axis=1).any()")
                # print("is nan row")
                # print("took %.2f sec" %(time()-t0))
                # break

            # y_range = [0, spec_array.max().compute().item()] # TODO: better scaling
            y_range = [0, signal_slice.attrs.get('y_max', spec_array.max().compute().item())]

            t0_i = float( spec_array.time[0] )
            t1_i = float( spec_array.time[-1] ) + float( period_array[-1] )

            print("Processing range: %s" %str((t0_i, t1_i)))

            t_data = {'request_id': request_id,}
            t_mark(t_data)
            # Put batch to queue to be visualized
            # generator_input_q.put({
            generator_input_cache.put({
                            'data': spec_array,
                            'filename': filename,
                            'viz_type': viz_type,
                            'mz_range': [mz0, mz1],
                            't_range': [t0_i, t1_i],
                            'y_range': y_range,
                            't_resolution': t_resolution,
                            'client_room': client_room,
                            'request_id': request_id,
                            'persist_in_cache': persist_in_cache,
                            **t_data
                            })

            processed_until = t1_i
            # print("Feed signal to visualize until: %s" %processed_until)
        return processed_until

    cache_item = cache.get(filename, None)
    if not cache_item:
        print("No such cache item: %s" %filename)
        return False
    if (mz0 == cache_item.attrs['range'][0] and
        mz1 == cache_item.attrs['range'][1] and
        not persist_in_cache
        ):
        processed_until = feed_ready_images()
    else:
        processed_until = feed_signal_to_visualize([t0, t1])
    return processed_until

def release_request(request_id):
        viz_cache_release('requests',
                          request_id=request_id,
                          )
        generator_input_cache.cache_delete_key(request_id)
        print(this_func_name(), request_id,
              'cache_q', generator_input_cache.cache.keys(),
              'file_cache', cache.keys())


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
            'acquisition_coordinates',
            'acquired_spectrum',
            'acquisition_finished',
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

        t_data = {'request_id': request_id,}
        t_mark(t_data)

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename) # TODO: Load a subset of arrays from file
            cache[filename] = cache_item

        if mz_range is None:
            # Full mz range
            mz_range = cache_item.attrs['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.attrs['length']]
            
        # Add a request, or add to existing request
        for viz_type in viz_types:
            viz_cache_put(filename,
                          viz_type,
                          t_range,
                          mz_range,
                          t_resolution,
                          client_room,
                          request_id
                          )
        # Process request
        viz_cache_process_requests(filename, request_id=request_id)

        t_mark(t_data)


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
        t_mark(value)
        for request_id in request_ids:
            release_request(request_id)
        # acquired samples are cached under filename key - check to release
        cur = viz_cache_get('requests', 'request_id', filename=filename)
        if not cur.fetchone() and filename in cache:
            del cache[filename]
    
    # ---------------------------------

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
        
        # Cache raw signal in memory
        mz = np.frombuffer( value['mz'], dtype=np.float32 )
        t_range = value['t_range']
        mz_range = [ float(mz[0]), float(mz[-1]) ]

        signal_array = ExtendableDataArray(array_module=da, persist=True)
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        period_array = ExtendableDataArray(array_module=da, persist=True)
        period_array.init_array(dims=('time'),
                                coords=[[]],
                                name='signal_period'
                                )
        # Collect attributes
        attributes = {'filename': filename_base,
                      'length': float(t_range[1]),
                      'range': mz_range,
                      }
        # Put to cache
        cache_item_dict = {'signal': signal_array,
                           'signal_period': period_array,
                           'attrs': attributes,
                           }

        # Initialize arrays for full-range visualizations to write to disk
        request_id = generate_unique_key()
        for viz_type in VIZ_TYPES_SUPPORTED:
            filename_viz = filename_to_zarr_path(filename_base, viz_type)
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
            filename_viz_period = filename_to_zarr_path(filename_base, viz_period)
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
            cache_item_dict.update({viz_type: viz_array,
                                    viz_period: viz_period_array
                                    })
            # Add a request
            viz_cache_put_or_update_request(filename_base,
                                            viz_type,
                                            t_range,
                                            mz_range,
                                            t_resolution=None,
                                            client_room='',
                                            request_id=request_id,
                                            persist_in_cache=True
                                            )

        cache_item = AttrDict(cache_item_dict)
        cache[filename_base] = cache_item

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
        viz_cache_process_requests(filename_base)
        return data['cnt']

    async def on_acquisition_finished(self, data):
        value = data['value']
        filename_base = value['filename']
        print("Finished acquiring file: %s" %filename_base)
        # TODO: Update request end times
        viz_cache_process_requests(filename_base, flush=True)



class DataVizServiceClient(BaseServiceClient):
    def __init__(self, url, port, client_namespace_data, n_jobs):
        super().__init__(url, port, client_namespace_data)
        self.n_jobs = n_jobs

    async def init_service(self):
        global generator_input_q
        global shutdown_event
        global generator_input_cache

        generator_input_q = Queue()
        self.generator_input_q =  Queue()
        shutdown_event = Event()
        generator_input_cache = CacheQ('request_id/viz_type',
                                    generator_input_q,
                                    self.generator_input_q,
                                    shutdown_event
                                    )
        self.generator_output_q = Queue()
        self.generator_procs = []

        for i in range(self.n_jobs):
            self.log("ImageGenerator %s/%s" %(i+1, self.n_jobs))
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
            except KeyboardInterrupt:
                break

            t_mark(img_data)

            # Got new image
            persist_in_cache = img_data.pop('persist_in_cache', None)

            if persist_in_cache:
                global cache
                # Cache image
                filename = img_data['filename']
                viz_type = img_data['viz_type']
                ti = np.array([ img_data['t_range'][0] ], dtype=np.float32)
                img_str = img_data.get('img') or json.dumps(img_data.get('traces'))
                img_period = img_data['t_range'][1] - img_data['t_range'][0]

                try:
                    viz_array = cache[filename][viz_type]
                    period_array = cache[filename][ (viz_type + '_period') ]
                except KeyError:
                    print("Key error! cache keys: %s" %str(list(cache.keys())))
                viz_array.extend_array(np.array([img_str]),
                                       [ti],
                                       'time'
                                       )
                period_array.extend_array(np.array( [img_period], dtype=np.float32 ),
                                          [ti],
                                          'time'
                                          )
                viz_cache_process_requests(filename=filename,
                                           persist_in_cache=False
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
                                  (args['ns'], DataVizServiceNamespace),
                                  int( args.get('n_jobs', cpu_count()) )
                                  )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
        # shutdown_event.set()
    # except Exception as e:
    #     print(f"Exception '{str(e)}' for {client.__class__.__name__}")
        # shutdown_event.set()
    finally:
        print(f'Stopping service with generators...')
        shutdown_event.set()
        for gen in client.generator_procs:
            gen.queue_in.put(None)



if __name__=='__main__':
    run()
