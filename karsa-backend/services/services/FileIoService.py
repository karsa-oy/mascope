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
import xarray
import zarr
import numpy as np
import dask.array as da
from multiprocessing import Lock
from collections import namedtuple
from PIL import Image
from copy import deepcopy

from karsalib import BaseClientNamespace, BaseServiceClient, \
                     parse_cmd_args, get_client_notification_args
from karsatof.kcollector import ExtendableDataArray
from karsatof.kdatapool import DataPool, parse_path_from_sample_name
from karsatof.kimage import (convert_base64_to_img, convert_to_base64)


NO_DATA_LOGGING_DEFAULT = True


# cache = dict(fname=dict(object_name={'item'=None,
#                                      'owners'=dict(sid={'ranges': [],
#                                                        'env': dict()
#                                                         }
#                                                    )
#                                      }
#                         )
#              )

cache = {}
client = None

# ========== Cache methods ==========

def log_cache(func):
    def wrapper(*args, **kwargs):
        global cache
        print("="*50)
        print("[%s](fname=%s, sid=%s, ranges=%s, obj_name=%s)"
              %(func.__name__, *cache_get_keys(args[0]), args[1])
              )
        print("cache before: %s" %str(cache))
        res = func(*args, **kwargs)
        print("-"*50)
        print("cache after: %s" %str(cache))
        print("-"*50)
        print("return: %s" %str(res))
        print("="*50)
        print(" "*50)
        return res
    return wrapper

def cache_get_keys(data):
    sid = data['cookies']['src_sid'][0]
    fname = data['value'].get('filename', None)
    mz_range = data['value'].get('mz_range', None)
    t_range = data['value'].get('t_range', None)
    ranges = str( [mz_range, t_range] )
    return fname, sid, ranges

def cache_contains(data, obj_name):
    global cache
    fname, sid, ranges = cache_get_keys(data)
    return (fname in cache and
            obj_name in cache[fname] and
            sid in cache[fname][obj_name]['owners'] and
            ranges in cache[fname][obj_name]['owners'][sid]['ranges']
            )

# @log_cache
def cache_get(data, obj_name):
    global cache
    if isinstance(data, list):
        fname, sid, ranges = data
    else:
        fname, sid, ranges = cache_get_keys(data)
    try:
        # Get object
        obj = cache[fname][obj_name]['item']
    except KeyError:
        # Object not in cache
        return None, None
    try:
        # Get sid-specific env
        env = cache[fname][obj_name]['owners'][sid]['env']
    except KeyError:
        # sid-level reference missing, add
        env = {}
        cache[fname][obj_name]['owners'][sid] = {'ranges': {}, 'env': env}
    if ranges:
        if ranges not in cache[fname][obj_name]['owners'][sid]['ranges']:
            # Add ranges
            cache[fname][obj_name]['owners'][sid]['ranges'][ranges] = {}
        # range-specific env
        env = cache[fname][obj_name]['owners'][sid]['ranges'][ranges]
    return obj, env

# @log_cache
def cache_put(data, obj_name, obj):
    """
    Add a new cache item under 'fname' key, with references to 'sid' and 'ranges'.
    """
    global cache
    fname, sid, ranges = cache_get_keys(data)

    if fname in cache and cache[fname].get(obj_name):
        # Cache item exists already
        if obj != cache[fname][obj_name]['item']:
            raise ValueError("Putting new object on top of existing one not allowed:",
                             f"{obj} vs. {cache[fname][obj_name]['item']}")
        if sid not in cache[fname][obj_name]['owners']:
            # Add sid
            cache[fname][obj_name]['owners'][sid] = {'ranges': {},
                                                     'env': {}
                                                     }
        if ranges not in cache[fname][obj_name]['owners'][sid]['ranges']:
            # Add ranges
            cache[fname][obj_name]['owners'][sid]['ranges'][ranges] = {}
    else:
        # Add new item to cache
        if fname not in cache:
            cache[fname] = {}
        cache[fname][obj_name] = {
            'item': obj,
            'owners': {sid: {'ranges': {ranges: {}} if ranges else {},
                             'env': {},
                             },
                       },
        }

# @log_cache
def cache_release(data, obj_name=None):
    """
    Method for releasing references to a cached resource, based on the presence of
    'fname'/'obj_name'/'sid'/'ranges' keys in 'data'.

    If 'obj_name' is given, references are only released to the specified object.
    Otherwise references to all objects are released under the following conditions:

    If 'ranges' are given in 'data', only the references to the particular ranges 
    in 'fname'/'obj_name' are released.
    If no 'ranges' but 'sid' is given, all references of the 'sid' in 'fname'/'obj_name'
    are released.
    If only 'filename' is given, all references to the file are released.
    If no references to 'fname' or 'object' are left, they are released from the cache.
    """
    global cache
    fname, sid, ranges = cache_get_keys(data)

    if fname:
        # Release references to specific file
        keys = [fname]
    else:
        # Release references to all files
        keys = list(cache.keys())

    # Loop through file(s)
    for key in keys:
        if obj_name:
            # Release references to specific object
            objs = [obj_name]
        else:
            # Release references to all objects
            objs = list(cache.get(key, {}).keys())
        # Loop through object(s)
        for obj in objs:
            try:
                if ranges != '[None, None]':
                    # Remove ref to specific ranges
                    cache[key][obj]['owners'][sid]['ranges'].pop(ranges)
                    # Check if 'sid' still has some refs to the object    
                    if not cache[key][obj]['owners'][sid]['ranges']:
                        # After removing specifief range, no refs left
                        # for this sid, remove from owners
                        cache[key][obj]['owners'].pop(sid)
                elif sid:
                    # Remove all sid refs to the cache item
                    cache[key][obj]['owners'].pop(sid)
                elif fname:
                    # Remove file completely from cache
                    cache.pop(fname)
                # Remove object if it does not have any references anymore
                if not cache[key][obj]['owners']:
                    cache[key].pop(obj)
            except KeyError:
                pass
        # Remove file from cache if it has no objects
        if not cache.get(key):
            cache.pop(key, None)
    
async def kill_cache(data):
    signal_array, _ = cache_get(data, 'signal')
    tps_array, _ = cache_get(data, 'tps')
    cache_release(data)
    if isinstance(signal_array, ExtendableDataArray):
        await signal_array.flush()
    if isinstance(tps_array, ExtendableDataArray):
        await tps_array.flush()

# -------------------------------------

class FileIoNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    endpoints = [
        # TOFService
        'acquisition_coordinates',
        'acquired_spectrum',
        'acquired_tps_data',
        'acquisition_finished',
        'tps_parameter_info',
        #
        # DataViz
        'data_request',
        'image_to_save',
        'stop_data_request',
        'tps_data_request',
        #
        # Router
        'service_state',
        #
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

        value = data['value']
        filename_base = value.get('filename')
        print("Start acquiring sample: %s" %filename_base)
        filename = base_to_zarr_filename(filename_base, 'signal')
        
        print("Writing signal into: %s" %filename)

        mz = np.frombuffer( value.get('mz'), dtype=np.float32 )
        signal_array = ExtendableDataArray(path=filename,
                                           array_module=da
                                           )
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        cache_put(data,
                  'signal',
                  signal_array,
                  )
        cache_put(data,
                  'full_t_range',
                  value.get('t_range')
                  )

        # Repeat the notification into root ns for DataViz
        await self.emit_client_notification('acquisition_coordinates',
                                             value,
                                             namespace='/'
                                             )

    async def on_acquired_spectrum(self, data):
        """Receive new spectrum, add to cache

        Parameters
        ----------
        data : dict
            keys: 'filename', 'i', 't' and 'spec'
        """
        # Get package index
        value = data['value']
        i = value.get('i')
        filename_base = value.get('filename')

        ti = np.array( [value.get('t')], dtype=np.float32 )
        spec = np.frombuffer(value.get('spec'), dtype=np.float32)
        spec = spec.reshape(-1, 1)
        signal_array, _ = cache_get(data, 'signal')
        if signal_array:       # TODO: signal_array is None on killing acquisition from MainUI
            print(i)
            mz = signal_array.data_array.mz
            await signal_array.extend_array(spec,
                                            [mz, ti],
                                            'time'
                                            )
        else:
            Warning("[on_acquired_spectrum]: signal_array is None")
        
        # Repeat the notification into root ns for DataViz
        await self.emit_client_notification('acquired_spectrum',
                                             value,
                                             namespace='/'
                                             )

    async def on_acquired_tps_data(self, data):
        value = data['value']
        filename_base = value.get('filename')
        ti = np.array( [value.get('t')], dtype=np.float32 )
        tps_data = np.frombuffer( value.get('data'), dtype=np.float32)
        tps_data = tps_data.reshape(-1, 1)
        tps_array, _ = cache_get(data, 'tps')
        if tps_array:   # TODO: tps_array is None on killing acquisition from MainUI
            tps_info = tps_array.data_array.parameter
            await tps_array.extend_array(tps_data,
                                        [tps_info, ti],
                                        'time'
                                        )

    async def on_acquisition_finished(self, data):
        global cache
        value = data['value']
        filename_base = value.get('filename')
        filename = base_to_zarr_filename(filename_base, 'signal')
        print("Finished acquiring file: %s" %filename)
        signal_array, _ = cache_get(data, 'signal')
        tps_array, _ = cache_get(data, 'tps')
        cache_release(data)
        if signal_array:
            await signal_array.flush()  # TODO: signal_array is None on killing acquisition from MainUI
        else:
            Warning("[on_acquistion_finished]: signal_array is None")
        if tps_array:
            await tps_array.flush()      # TODO: tps_array is None on killing acquisition from MainUI
        else:
            Warning("[on_acquistion_finished]: tps_array is None")
        
        # Repeat the notification into root ns for DataViz
        await self.emit_client_notification('acquisition_finished',
                                             value,
                                             namespace='/'
                                             )

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
    async def on_data_request(self, data):
        # print("Data request:", data)
        value = data['value']
        kwargs = get_client_notification_args(data)

        try:
            filename = value['filename']
        except KeyError:
            print("KeyError: %s" %value)
            return
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

        set_figure_ranges = False
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
        if set_figure_ranges:
            # Full range request, try to load images from file and send to DataViz
            try:
                heatmap_img = load_heatmap_image(filename)
                spec_imgs = load_spec_trace_images(filename)
                await self.emit_client_notification('heatmap_image',
                                                    {'filename': filename,
                                                     'mz_range': mz_range,
                                                     't_range': t_range,
                                                     'img': heatmap_img
                                                     },
                                                    **{**kwargs,
                                                           'namespace': '/',
                                                           'no_data_logging': True
                                                           }
                                                        )
                for t0, spec_img in spec_imgs:
                    await self.emit_client_notification('spec_trace_image',
                                                        {'filename': filename,
                                                         'mz_range': mz_range,
                                                         't_range': [t0, t0], # t1 does not matter
                                                         'img': spec_img
                                                         },
                                                        **{**kwargs,
                                                           'namespace': '/',
                                                           'no_data_logging': True
                                                           }
                                                        )
                # No need to send data to DataViz
                stream_data = False
            except Exception as e:
                print(e)

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

    async def on_image_to_save(self, data):
        value = data['value']
        filename = value['filename']
        img_filename = value['img_filename']
        img_str = value['img']
        sample_data_path = parse_path_from_sample_name(filename)
        img_path = os.path.join(sample_data_path, img_filename)
        img = convert_base64_to_img(img_str)
        img.save(img_path)

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


class FileIoClient(BaseServiceClient):
    pass

def run():
    global client

    url, port, namespace = parse_cmd_args()
    # FileIo should always be in private namespace with data producer
    if namespace == '/':
        print("FileIoService must be in a private namespace. " +
              "Please restart the service with --ns option."
              )
        return

    client = FileIoClient(url, port, (namespace, FileIoNamespace))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
