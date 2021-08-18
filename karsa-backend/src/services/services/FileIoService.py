# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization.
      
Created on Thu May  7 12:43:13 2020
"""

import os
import time
import asyncio
import fnmatch
import json
import xarray
import zarr
import numpy as np
import dask.array as da


from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.logging import t_mark
from karsalib.struct import AttrDict, ExtendableDataArray, LRUDict
from karsalib.util import (
                        get_client_notification_args,
                        parse_cmd_args
                        )

from karsalib.datapool import parse_path_from_sample_name



DATA_VERSION_NUMBER = '0.01'



client = None

# Cache for data arrays
cache = LRUDict(10)


class FileIoNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    endpoints = [
        # TOFControl
        'instrument_log_entry',
        'instrument_log_request',
        # //
        # TOFService
        'acquisition_coordinates',
        'acquired_spectrum',
        'acquired_tps_data',
        'acquisition_finished',
        'tps_parameter_info',
        # //
        # Router
        'service_state',
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

        filename_signal = filename_to_zarr_path(filename_base, 'signal')

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
        filename_period = filename_to_zarr_path(filename_base, 'signal_period')
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
        # print("cache: %s" %str(cache))

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

    async def on_acquired_tps_data(self, data):
        global cache

        value = data['value']
        filename_base = value.get('filename')
        ti = np.array( [value.get('t')], dtype=np.float32 )
        tps_data = np.frombuffer( value.get('data'), dtype=np.float32)
        tps_data = tps_data.reshape(-1, 1)
        tps_array = cache[filename_base].tps
        tps_info = tps_array.parameter
        tps_array.extend_array(tps_data,
                               [tps_info, ti],
                               'time'
                               )

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

    async def on_tps_parameter_info(self, data):
        global cache

        value = data['value']
        filename_base = value.get('filename')
        filename = filename_to_zarr_path(filename_base, 'tps')

        print("Writing TPS data into: %s" %filename)

        tps_info = value.get('tps_info')
        
        tps_array = ExtendableDataArray(path=filename,
                                        array_module=da
                                        )
        tps_array.init_array(dims=('parameter', 'time'),
                             coords=[tps_info, []],
                             name='tps'
                             )
        cache_item = cache[filename_base]
        cache_item.update({'tps': tps_array})
        cache[filename_base] = cache_item
    # -----------------------------------------


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

def filename_to_zarr_path(base_filename, variable):
    sample_data_path = parse_path_from_sample_name(base_filename)
    zarr_filename = variable + os.extsep + 'zarr'
    return os.path.join(sample_data_path, zarr_filename)

def get_file_data_vars(filepath):
    file_dirs = next(os.walk(filepath))[1]
    zarrs = []
    for var in fnmatch.filter(file_dirs, '*.zarr'):
        zarrs.append(var.strip('.zarr'))
    return zarrs

def load_array(base_filename, var):
    """Load a stored variable in a file into a xarray.Dataset object

    Parameters
    ----------
    base_filename : str
        Base filename
    var : str
        Variable (zarr array) name

    Returns
    -------
    xarray.Dataset
        Loaded data
    """
    print("Loading array: %s from file: %s" %(base_filename, var))
    var_path = filename_to_zarr_path(base_filename, var)
    # Load data from file
    try:
        dataset = open_mfzarr(var_path)
    except FileNotFoundError as e:
        print("FileNotFoundError: Error reading %s, %s" %(var_path, e))
    return dataset

def load_file(base_filename, vars=None):
    """Load all stored variables in a file into a xarray.Dataset object

    Parameters
    ----------
    base_filename : str
        Base filename
    vars : list, optional
        List of variable (zarr array) names to load. By default None,
        all variables are loaded.

    Returns
    -------
    xarray.Dataset
        Loaded data
    """
    filepath = parse_path_from_sample_name(base_filename)
    if vars is None:
        # Get all saved variable names
        zarrs = get_file_data_vars(filepath)
        vars = [ zarr.strip('.zarr') for zarr in zarrs ]
    print("Loading variables: %s file: %s" %(str(vars), base_filename))
    # Load data from file
    dss = []
    for var in vars:
        try:
            var_ds = load_array(base_filename, var)
            dss.append(var_ds)
        except Exception as e:
            print("Failed to load data: %s" %e)
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
        raise FileNotFoundError("Zarr file %s does not exist" %path)
    sync = zarr.ProcessSynchronizer(os.path.join(path, '.sync'))
    z = zarr.open(path, mode=mode, synchronizer=sync)
    groups = [ g[0] for g in z.groups() ]
    x = xarray.concat([ xarray.open_zarr(path, g) for g in groups ],
                      concat_dim
                      )
    x.attrs = z.attrs.asdict()
    return x
    
def read_zarr_attributes(filepath):
    if not os.path.exists(filepath):
        raise ValueError("Zarr file %s does not exist" %filepath)
    sync = zarr.ProcessSynchronizer(os.path.join(filepath, '.sync'))
    z = zarr.open(filepath, mode='r', synchronizer=sync)
    attributes = z.attrs.asdict()
    return attributes

def write_zarr_attributes(filepath, attributes):
    if not os.path.exists(filepath):
        raise ValueError("Zarr file %s does not exist" %filepath)
    sync = zarr.ProcessSynchronizer(os.path.join(filepath, '.sync'))
    z = zarr.open(filepath, mode='a', synchronizer=sync)
    z.attrs.update(attributes)
# ---------------------------------------


class FileIoClient(BaseServiceClient):
    
    async def init_service(self):
        return

    async def service_main(self):
        while True:
            try:
                await self.sio.sleep(.5)
            except KeyboardInterrupt:
                break
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
                          (args['ns'], FileIoNamespace)
                          )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        print(f'Service stopped.')



if __name__=='__main__':
    run()
