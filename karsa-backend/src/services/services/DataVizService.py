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
import ntpath
import os
from re import I
import re
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
from time import time, sleep

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.struct import AttrDict, CacheQ, LRUDict
from karsalib.util import (generate_unique_key,
                           get_client_notification_context,
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

from services.FileIoService import filename_to_zarr_path, load_file, zarr_sdk


NO_DATA_LOGGING_DEAULT = False
client = None

# Cache for data arrays
cache = LRUDict(10)

generator_input_q = None
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

    # requests_to_release = []
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
    #     else:
    #         requests_to_release.append(request_id)
    # if requests_to_release:
    #     # check requests_to_release are processed for all viz_types, then release
    #     for id in set(requests_to_release):
    #         cur = viz_cache_get('requests', 'request_id', request_id=id)
    #         if not cur.fetchone():
    #             force_release_request(id)
    #     # # samples in proc are cached under filename key - check if any request uses the sample
    #     # cur = viz_cache_get('requests', 'request_id', filename=filename)
    #     # if not cur.fetchone() and filename in cache:
    #     #     del cache[filename]   # TODO: can not delete, since some cleanup may be on the way


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
        except KeyError as e:
            print("KeyError: %s , when slicing %s ; cache_items: %s" % (e, viz_type, list(cache_item.keys())) )
            return False
        try:
            period_slice = cache_item[viz_type_period].sel(time=slice(t0, t1)).load()
        except KeyError as e:
            print("KeyError: %s , when slicing %s ; cache_items: %s" % (e, viz_type_period, list(cache_item.keys())) )
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

            print(f"Processing {filename}/{viz_type} range: {[t0_i, t1_i]}")

            t_data = {'request_id': request_id,}
            t_mark(t_data)
            # Put batch to queue to be visualized
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
    if (mz0 == cache_item.props['range'][0] and
        mz1 == cache_item.props['range'][1] and
        not persist_in_cache
        ):
        processed_until = feed_ready_images()
    else:
        processed_until = feed_signal_to_visualize([t0, t1])
    return processed_until

def force_release_request(request_id):
    # Force releasing cache - needed to interrupt workflow,
    # in a normal mode cache cleans up by itself.
    viz_cache_release('requests',
                        request_id=request_id,
                        )
    generator_input_cache.cache_delete_key(request_id)


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
            'dataset_updated',
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
            mz_range = cache_item.props['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.props['length']]
            
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
            force_release_request(request_id)
        # acquired samples are cached under filename key - check to release
        cur = viz_cache_get('requests', 'request_id', filename=filename)
        if not cur.fetchone() and filename in cache:
            del cache[filename]

    
    # ------Streamer/FileIo request---------------

    async def on_dataset_updated(self, data):
        # trigger full-size image with every commit of signal dataset
        def update_cache_item(dataset, item_to_update=None):
            if not item_to_update:
                return AttrDict({
                    'dataset': dataset,
                    'signal': dataset.signal,
                    'signal_period': dataset.signal_period,
                    'props': dataset.attrs['props'],
                })
            else:
                item_to_update.dataset = dataset
                try:
                    item_to_update.signal = dataset.signal
                except:
                    pass    # sometimes signal data is not ready yet
                try:
                    item_to_update.signal_period = dataset.signal_period
                except:
                    pass
                item_to_update.props = dataset.attrs['props']
                return item_to_update

        def file_cache_is_missing_or_obsolete():
            item = cache.get(filename)
            if item is None:
                return True
            if item.props['length'] == item.props['committed_length'] != committed_length:
                return True
            return False

        value = data['value']
        if value['data_type'] != 'signal':
            raise ValueError(f"Expected data_type: signal - got {value['data_type']}")
        filename = value['filename']
        full_length = value['length']
        committed_length = value['committed_length']
        request_id = generate_unique_key()

        if file_cache_is_missing_or_obsolete():
            self.log('Reset cache for', filename)
            cache[filename] = {}

        if committed_length == 0:  # sample just created, not updated yet
            self.log('Ready for visualizing', filename)
            # cache[filename] = {}
        elif committed_length != full_length:  # sample is updated
            cache_item = cache.get(filename)
            if not cache_item:
                self.log(f"Start visualizing {filename} up to {committed_length}")
                try:
                    ds = load_file(filename, vars=['signal', 'signal_period'])
                except Exception as e:
                    self.log(f"Failed visualizing {filename} up to {committed_length}: {str(e)}")
                    if cache_item:
                        cache_item['crippled'] = True
                    return
                cache_item = update_cache_item(ds)
                for viz_type in VIZ_TYPES_SUPPORTED:
                    zarr_sdk.init_viz_dataset(filename, viz_type, cache_item)
                    viz_cache_put_or_update_request(
                        filename,
                        viz_type,
                        t_range=[0, full_length],
                        mz_range=value['range'],
                        t_resolution=None,
                        client_room='',
                        request_id=request_id,
                        persist_in_cache=True
                    )
                cache[filename] = cache_item
            else:
                self.log(f"Continue visualizing {filename} up to {committed_length}")
                try:
                    ds = load_file(filename, vars=['signal', 'signal_period'], prev_dataset=cache_item['dataset'])
                except Exception as e:
                    self.log(f"Failed visualizing {filename} up to {committed_length}: {str(e)}")
                    cache_item['crippled'] = True
                    return
                update_cache_item(ds, cache_item)
            viz_cache_process_requests(filename)
        elif committed_length == full_length:  # sample is done
            self.log(f"Finish visualizing {filename}: final length {committed_length}")
            viz_cache_process_requests(filename, flush=True)
            cache_item = cache.get(filename)
            if cache_item:
                if cache_item.get('crippled', False):
                    del cache[filename]   # don't leave crippled item in file cache
                else:
                    cache[filename]['props']['length'] = full_length
                    cache[filename]['props']['committed_length'] = committed_length


class DataVizServiceClient(BaseServiceClient):
    def __init__(self, url, port, client_namespace_data, n_jobs):
        super().__init__(url, port, client_namespace_data)
        self.n_jobs = n_jobs

    async def init_service(self):
        global generator_input_q
        global generator_input_cache

        generator_input_q = Queue()
        self.generator_input_q =  Queue()
        generator_input_cache = CacheQ('request_id/viz_type',
                                    generator_input_q,
                                    self.generator_input_q,
                                    self.shutdown_event
                                    )
        self.generator_output_q = Queue()
        self.generator_procs = []

        for i in range(self.n_jobs):
            self.log("ImageGenerator %s/%s" %(i+1, self.n_jobs))
            gen_proc = ImageGenerator(self.generator_input_q,
                                      self.generator_output_q,
                                      self.shutdown_event
                                      )
            gen_proc.start()
            self.generator_procs.append(gen_proc)
            await self.sio.sleep(1)


    async def service_main(self):
        global cache

        # start input cache thread
        generator_input_cache.start()

        while not self.shutdown_event.is_set():
            # Check queues for new images
            try:
                img_data = self.generator_output_q.get_nowait()
            except Empty:
                await self.sio.sleep(.1)
                continue
            except KeyboardInterrupt:
                self.log('KeyboardInterrupt')
                break
            except Exception as e:
                self.log(str(e))
                break

            t_mark(img_data)

            # Got new image
            persist_in_cache = img_data.pop('persist_in_cache', False)
            if persist_in_cache:
                # Cache image
                filename = img_data['filename']
                cache_item = cache.get(filename)
                if not cache_item:
                    self.log(f"Skip visualizing {filename} - data not in cache.")
                else:
                    viz_type = img_data['viz_type']
                    ti = np.array([ img_data['t_range'][0] ], dtype=np.float32)
                    img_str = img_data.get('img') or json.dumps(img_data.get('traces'))
                    img_period = img_data['t_range'][1] - img_data['t_range'][0]
                    try:
                        viz_array = cache_item[viz_type]
                        period_array = cache_item[ (viz_type + '_period') ]
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
                    except KeyError as e:
                        self.log("Key error:", str(e))
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
        self.shutdown_event.set()
        self.log('stopped')
        # Terminate image generators: TODO: use self.shutdown_event here too
        [proc.terminate() for proc in self.generator_procs]
        await self.sio.disconnect()


def run():
    global client

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
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        print(f'Stopping service with generators...')
        client.shutdown_event.set()
        for gen in client.generator_procs:
            gen.queue_in.put(None)



if __name__=='__main__':
    run()
