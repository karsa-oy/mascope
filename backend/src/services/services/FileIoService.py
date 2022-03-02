# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization.
      
Created on Thu May  7 12:43:13 2020
"""

import os
import asyncio
import fnmatch
import json
import xarray
import zarr
import numpy as np
import dask.array as da

from ctypes import ArgumentError
from shutil import rmtree

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.datapool import (METADATA_VERSION_NUMBER,
                               parse_path_from_item_filename,
                               )
from karsalib.logging import this_func_name
from karsalib.struct import AttrDict, ExtendableDataArray, LRUDict
from karsalib.util import get_client_notification_context, parse_cmd_args


DATA_VERSION_NUMBER = '0.01'


client = None

# Cache for data arrays
cache = LRUDict(10)



class zarr_sdk:
    @staticmethod
    def finalize_signal_dataset(data, item):
        filename = data['value']['filename']
        try:
            final_length = float(item['signal'].time[-1] + item['signal_period'][-1])
        except Exception as e:
            print(f"[{this_func_name}] Warning: {e.__class__.__name__}({str(e)})")
            final_length = item['props']['length']

        # Update properties
        final_length = min(final_length, item['props']['length'])
        item['props'].update({'committed_length': final_length})
        item['props'].update({'length': final_length})
        # Write properties
        update_props(filename, item['props'])
        # flush arrays
        arrays = [item['signal'], item['signal_period']]
        for a in arrays:
            if isinstance(a, ExtendableDataArray):
                a.flush()

    @staticmethod
    def init_centroid_dataset(data, item):
        value = data['value']
        filename = filename_to_zarr_path(value['filename'], 'centroids')
        filename = os.path.join(item.get('data_root', ''), filename)
        centroid_array = ExtendableDataArray(path=filename,
                                             array_module=da
                                             )
        centroid_array.init_array(dims=('mz', 'time'),
                                  coords=[[], []],
                                  name='centroids'
                                  )
        item.update({'centroids': centroid_array})

    @staticmethod
    def init_signal_dataset(data, data_root='', overwrite=False):
        # First filesystem operation in acquisition api sequence:
        #   init_signal_dataset - init_tps_dataset - init_viz_dataset -
        #   update_signal_dataset - update_tps_dataset - finalize_signal_dataset
        # Returns acquisition item shared through the acquisiiton api
        value = data['value']
        filename = value.get('filename')
        mz = np.frombuffer( value['mz'], dtype=np.float32 )
        t_range = value['t_range']

        data_path = parse_path_from_item_filename(filename)
        data_path = os.path.join(data_root, data_path)
        if os.path.exists(data_path):
            if overwrite:
                rmtree(data_path)
            else:
                raise FileExistsError(data_path)
        filename_signal = filename_to_zarr_path(filename, 'signal')
        filename_signal = os.path.join(data_root, filename_signal)
        signal_array = ExtendableDataArray(path=filename_signal,
                                            array_module=da
                                            )
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        filename_period = filename_to_zarr_path(filename, 'signal_period')
        filename_period = os.path.join(data_root, filename_period)
        period_array = ExtendableDataArray(path=filename_period,
                                            array_module=np
                                            )
        period_array.init_array(dims=('time'),
                                coords=[[]],
                                name='signal_period'
                                )
        properties = {'filename': filename,
                        'length': float(t_range[1]),
                        'committed_length': 0.,
                        'range': [ float(mz[0]), float(mz[-1]) ],
                        'data_version': DATA_VERSION_NUMBER,
                        'metadata_version': METADATA_VERSION_NUMBER,
                    }
        write_props(filename, properties)

        return {'data_root': data_root,
                'signal': signal_array,
                'signal_period': period_array,
                'props': properties,
                }

    @staticmethod
    def init_tps_dataset(data, item):
        value = data['value']
        filename = filename_to_zarr_path(value['filename'], 'tps')
        filename = os.path.join(item.get('data_root', ''), filename)
        tps_info = value['tps_info']
        tps_array = ExtendableDataArray(path=filename,
                                        array_module=da
                                        )
        tps_array.init_array(dims=('parameter', 'time'),
                             coords=[tps_info, []],
                             name='tps'
                             )
        item.update({'tps': tps_array})

    @staticmethod
    def init_viz_dataset(filename_base, viz_type, item):
        # initialize viz_type mfzarr
        filename_viz = filename_to_zarr_path(filename_base, viz_type)
        filename_viz = os.path.join(item.get('data_root', ''), filename_viz)
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
        filename_viz_period = os.path.join(item.get('data_root', ''), filename_viz_period)
        viz_period_array = ExtendableDataArray(path=filename_viz_period,
                                                array_module=np,
                                                dtype=object,
                                                chunk_size=1,
                                                )
        viz_period_array.init_array(dims=('time',),
                                    coords=[[]],
                                    name=viz_period
                                    )
        item.update( {viz_type: viz_array, viz_period: viz_period_array} )

    @staticmethod
    def update_centroid_dataset(data, item):
        value = data['value']
        ti = np.array( [value['t']], dtype=np.float32 )
        period = np.array( [value['period']], dtype=np.float32 )
        # print(ti.item())
        c_y = np.frombuffer(value['peak_intensity'], dtype=np.float32)
        c_y = c_y.reshape(-1, 1)
        c_mz = np.frombuffer(value['peak_mz'], dtype=np.float32)
        c_mz = c_mz.reshape(-1,)

        # Extend data arrays (write to file)
        item['centroids'].extend_array(c_y,
                                       [c_mz, ti],
                                       'time'
                                       )
        # item['centroid_period'].extend_array(period,
        #                                     [ti],
        #                                     'time'
        #                                     )

    @staticmethod
    def update_signal_dataset(data, item):
        value = data['value']
        ti = np.array( [value['t']], dtype=np.float32 )
        period = np.array( [value['period']], dtype=np.float32 )
        # print(ti.item())
        spec = np.frombuffer(value['spec'], dtype=np.float32)
        spec = spec.reshape(-1, 1)
        if 'mz' in value:
            # mz coordinates provided with data (Orbitrap)
            mz = np.frombuffer(value['mz'], dtype=np.float32)
            mz = mz.reshape(-1,)
        else:
            # Use mz coordinates from signal_array (TOF)
            mz = item['signal']['mz']
        # Extend data arrays (write to file)
        item['signal'].extend_array(spec,
                                    [mz, ti],
                                    'time')
        item['signal_period'].extend_array(period,
                                            [ti],
                                            'time')
        # Update committed_length in .props, when new chunk is committed
        if item['signal'].delayed_write is None:
            committed_length = float(item['signal'].time[-1] + item['signal_period'][-1])
            item['props'].update({'committed_length': committed_length})
            prop_path = os.path.join(item.get('data_root', ''),
                                    parse_path_from_item_filename(value['filename']),
                                    '.props')
            with open(prop_path, 'w') as f:
                json.dump(item['props'], f, indent=4)

    @staticmethod
    def update_tps_dataset(data, item):
        value = data['value']
        ti = np.array( [value.get('t')], dtype=np.float32 )
        tps_data = np.frombuffer( value.get('data'), dtype=np.float32)
        tps_data = tps_data.reshape(-1, 1)
        tps_info = item['tps']['parameter']
        item['tps'].extend_array(tps_data,
                                [tps_info, ti],
                                'time'
                                )

    @staticmethod
    def write_peak_dataset(peak_profiles, item):
        filename_base = item.props['filename']
        filename = filename_to_zarr_path(filename_base, 'peaks')
        peaks_array = ExtendableDataArray(path=filename
                                          )
        peaks_array.init_array(dims=('mz', 'time'),
                               data=peak_profiles,
                               coords=[peak_profiles.mz, peak_profiles.time],
                               name='peaks'
                               )

class FileIoNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    service_state = dict()

    # ========== TOFControl requests ==========

    # # TODO: REMOVE_THIS - this code is left as example for call_client_notification
    # async def on_raw_metadata_request(self, data):
    #     return data['value'] + ' - Pong'

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
        filename = data['value']['filename']
        self.log(filename)
        kwargs = get_client_notification_context(data)
        try:
            cache_item = zarr_sdk.init_signal_dataset(data)
        except FileExistsError:
            self.log(f"FileExistsError: {filename} acquisition cancelled")
            await self.emit_client_notification('stop_raw_import', {}, **kwargs)
            return {}
        cache_item = AttrDict(cache_item)
        cache[filename] = cache_item
        return data['callback_data']


    async def on_acquired_spectrum(self, data):
        """Receive new spectrum, add to cache

        Parameters
        ----------
        data : dict
            keys: 'filename', 'i', 't', 'spec', 'period', ('mz')
        """
        global cache
        filename = data['value']['filename']
        cache_item = cache.get(filename)
        kwargs = get_client_notification_context(data)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        zarr_sdk.update_signal_dataset(data, cache_item)
        if cache_item['signal'].delayed_write is None :
            # updates to signal mfzarrs are committed - notify
            await self.emit_client_notification(
                    'dataset_updated',
                    {'data_type': 'signal', **cache_item['props']},
                    # TODO: switch to private notification after moving DataViz to private_ns
                    **{ **kwargs,
                        'namespace': '/',
                        'room': None,
                    }
                  )
        return data['callback_data']


    async def on_acquired_tps_data(self, data):
        global cache
        filename = data['value']['filename']
        cache_item = cache.get(filename)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        zarr_sdk.update_tps_dataset(data, cache_item)


    async def on_acquisition_finished(self, data):
        global cache
        filename = data['value']['filename']
        cache_item = cache.get(filename)
        kwargs = get_client_notification_context(data)
        self.log(filename)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        try:
            zarr_sdk.finalize_signal_dataset(data, cache_item)
        except:
            pass    # let client services finalize the request anyway
        await self.emit_client_notification(
                'dataset_updated',
                {'data_type': 'signal', **cache_item['props']},
                # TODO: switch to private notification after moving DataViz to private_ns
                **{ **kwargs,
                    'namespace': '/',
                    'room': None,
                }
            )


    async def on_tps_parameter_info(self, data):
        global cache
        filename = data['value']['filename']
        self.log(filename)
        cache_item = cache.get(filename)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        zarr_sdk.init_tps_dataset(data, cache_item)
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
    sample_data_path = parse_path_from_item_filename(base_filename)
    zarr_filename = variable + os.extsep + 'zarr'
    return os.path.join(sample_data_path, zarr_filename)

def get_file_data_vars(filepath):
    file_dirs = next(os.walk(filepath))[1]
    zarrs = []
    for var in fnmatch.filter(file_dirs, '*.zarr'):
        zarrs.append(var.strip('.zarr'))
    return zarrs

def get_zarr_var_shape(base_filename, var, concat_dim=1):
    path = filename_to_zarr_path(base_filename, var)
    if not os.path.exists(path):
        raise FileNotFoundError("Zarr file %s does not exist" %path)
    sync = ExtendableDataArray.get_zarr_synchronizer(path)
    z = zarr.open(path, mode='r', synchronizer=sync)
    group_shapes = [ g[1][var].shape for g in z.groups() ]
    dim0, dim1 = zip(*group_shapes)
    if concat_dim == 0:
        shape = (sum(dim0), max(dim1))
    elif concat_dim == 1:
        shape = (max(dim0), sum(dim1))
    else:
        raise ArgumentError("Error in 'get_zarr_var_shape()', 'concat_dim' must be 0 or 1")
    return shape
    
def load_array(base_filename, var, prev_array=None):
    """Load a stored mfzarr variable from file into a xarray.Dataset object.
       If the variable receives another chunk of mfzarr data, then subsequent
       load_array calls with non-empty prev_array will update
       previously created dataset from the updated variable.

    Parameters
    ----------
    base_filename : str
        Base filename
    var : str
        Variable (zarr array) name
    prev_array: xarray DataArray, optional
        Previously loaded array to update with the updated var. By default None.

    Returns
    -------
    xarray.Dataset
        Loaded data
    """
    # print("Loading array %s : %s" %(base_filename, var))
    var_path = filename_to_zarr_path(base_filename, var)
    if not os.path.exists(var_path):
        raise FileNotFoundError(var_path)
    # Load data from file
    def is_multifile():    
        z = zarr.open(var_path, mode='r', synchronizer=sync)
        groups = list(z.group_keys())
        return bool(len(groups))

    sync = ExtendableDataArray.get_zarr_synchronizer(var_path)
    if is_multifile():
        # Multi-file (grouped)
        dataset = open_mfzarr(var_path, prev_array=prev_array, sync=sync)
    else:
        # Single file
        dataset = open_zarr(var_path, sync=sync)

    return dataset

def load_coord(base_filename, var, coord_name):
    path = filename_to_zarr_path(base_filename, var)
    sync = ExtendableDataArray.get_zarr_synchronizer(path)
    z = zarr.open(path, mode='r', synchronizer=sync)
    coord = z[coord_name]
    return coord[:]

def load_file(base_filename, vars=None, prev_dataset=None):
    """Load stored mfzarr variables into an xarray.Dataset object.
       If the variables receive another chunk of data, then subsequent
       load_file calls with non-empty prev_dataset will update
       previously created dataset from updated variables.

    Parameters
    ----------
    base_filename : str
        Base filename
    vars : list, optional
        List of variable (zarr array) names to load. By default None,
        all variables are loaded.
    prev_dataset: xarray dataset, optional
        Previously loaded dataset to update with updated vars. By default None.

    Returns
    -------
    xarray.Dataset
        Loaded data
    """
    filepath = parse_path_from_item_filename(base_filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)
    if vars is None:
        # Get all saved variable names
        zarrs = get_file_data_vars(filepath)
        vars = [ zarr.strip('.zarr') for zarr in zarrs ]
    # Load arrays from mfzarrs
    print(f"Loading {vars} from {base_filename}")
    datasets = []
    zarr_groups = {}
    # Load requested data arrays
    for var in vars:
        prev_item = None if prev_dataset is None else prev_dataset.get(var)
        if prev_item is not None:
            prev_item.attrs['zarr_groups'] = prev_dataset.attrs.get('zarr_groups', {}).get(var, [])
        try:
            var_dataset = load_array(base_filename, var, prev_item)
        except FileNotFoundError as e:
            print(f"[{this_func_name()}] Error {base_filename}/{var}: {e.__class__.__name__}({str(e)})")
            continue
        datasets.append(var_dataset)
        zarr_groups[var] = var_dataset.attrs.get('zarr_groups', [])
    # Add previously loaded arrays
    if prev_dataset is not None:
        for prev_var, prev_var_dataset in prev_dataset.data_vars.items():
            if prev_var not in vars:
                datasets.append(prev_var_dataset)
    # Merge datasets per variable into one dataset
    dataset = xarray.merge(datasets)
    # Load properties
    prop_path = os.path.join(filepath, '.props')
    with open(prop_path, 'r') as f:
        props = json.load(f)
    # Attach to dataset
    dataset.attrs['props'] = props
    dataset.attrs['zarr_groups'] = zarr_groups
    return dataset

def open_mfzarr(path, sync=None, mode='r', concat_dim='time', prev_array=None):
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
    prev_array: xarray DataArray, optional
        Previously loaded array to update with new mfzarr data chunk,
        by default None.

    Returns
    -------
    xarray.Dataset
        Concatenated data

    Raises
    ------
    ValueError
        In case requested file does not exist
    """
    z = zarr.open(path, mode=mode, synchronizer=sync)
    groups = list(z.group_keys())

    if prev_array is not None:
        prev_groups = prev_array.attrs.get('zarr_groups', [])
        for g in prev_groups:
            # print('group %s already loaded' %g)
            groups.remove(g)
    # print(f"{os.path.basename(path)} {'loading' if prev_array is None else 'updating'} from group {groups}")
    if not groups:
        # print('no new groups')
        return prev_array
    # print("loading groups: %s" %groups)
    x = xarray.concat([xarray.open_zarr(path,
                                        g,
                                        consolidated=False,
                                        synchronizer=sync
                                        )
                       for g in groups
                       ],
                      concat_dim
                      )
    if prev_array is not None:
        x = xarray.concat([prev_array.to_dataset(), x], concat_dim)
    x.attrs = z.attrs.asdict()
    x.attrs['zarr_groups'] = groups
    return x
    
def open_zarr(path, sync=None):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ds = xarray.open_zarr(path, consolidated=False, synchronizer=sync)
    return ds

def read_zarr_attributes(filepath):
    if not os.path.exists(filepath):
        raise ValueError("Zarr file %s does not exist" %filepath)
    sync = ExtendableDataArray.get_zarr_synchronizer(filepath)
    z = zarr.open(filepath, mode='r', synchronizer=sync)
    attributes = z.attrs.asdict()
    return attributes

def update_props(base_filename, props_to_update):
    sample_data_path = parse_path_from_item_filename(base_filename)
    # Update properties
    prop_path = os.path.join(sample_data_path, '.props')
    with open(prop_path, 'r') as f:
        props = json.load(f)
    props.update(props_to_update)
    with open(prop_path, 'w') as f:
        json.dump(props, f, indent=4)

def write_props(base_filename, props):
    sample_data_path = parse_path_from_item_filename(base_filename)
    # Write properties
    prop_path = os.path.join(sample_data_path, '.props')
    with open(prop_path, 'w') as f:
        json.dump(props, f, indent=4)

def update_zarr_array_coord(base_filename, var, dim, coord):
    array_path = filename_to_zarr_path(base_filename, var)
    sync = ExtendableDataArray.get_zarr_synchronizer(array_path)
    zarr_array = zarr.open(array_path, mode='a', synchronizer=sync)
    zarr_array[dim][:] = coord
    for group_name, group in zarr_array.groups():
        group[dim][:] = coord

def write_zarr_attributes(filepath, attributes):
    if not os.path.exists(filepath):
        raise ValueError("Zarr file %s does not exist" %filepath)
    sync = ExtendableDataArray.get_zarr_synchronizer(filepath)
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
        client.shutdown_event.set()
        print(f'Service stopped.')



if __name__=='__main__':
    run()
