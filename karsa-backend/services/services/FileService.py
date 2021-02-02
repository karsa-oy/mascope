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
import xarray
import zarr
import numpy as np
import dask.array as da
from multiprocessing import Lock

from karsalib import BaseClientNamespace, BaseServiceClient, parse_cmd_args
from karsatof.kcollector import ExtendableDataArray
from karsatof.kdatapool import DataPool


NO_DATA_LOGGING_DEFAULT = True

# TODO: Make configuration file for the paths
# TODO: Change the global vars to class vars
data_path = 'Data'
projects_path = 'Projects'
datapool = DataPool(data_path, projects_path)
signal_cache = {}
tps_cache = {}


class FileServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    rooms = [
        'acquisition_coordinates',
        'acquired_spectrum',
        'acquired_tps_data',
        'acquisition_started',
        'acquisition_finished',
        'data_request',
        'stop_data_request',
        'experiment_selected',
        'experiments',
        'import_sample_table_datetime_range',
        'project_selected',
        'projects',
        'sample_attributes',
        'service_state',
        'tps_data_request',
        'tps_parameter_info',
        ]

    service_state = dict(
        projects = datapool.get_projects(),
    )

    # ========== UI requests ==========
    def cache_get_keys(self, cache, data):
        sid = data['cookies']['src_sid'][0]
        fname = data['value'].get('filename')
        return sid, fname

    def cache_contains(self, cache, data):
        sid, fname = self.cache_get_keys(cache, data)
        return sid in cache and fname in cache[sid]

    def cache_get(self, cache, data):
        sid, fname = self.cache_get_keys(cache, data)
        try:
            return cache[sid][fname]
        except KeyError:
            return None

    def cache_put(self, cache, data, array):
        sid, fname = self.cache_get_keys(cache, data)
        if sid not in cache:
            cache[sid] = {}
        cache[sid][fname] = array

    def cache_pop(self, cache, data):
        """
        Method for releasing cached resource. The value is released
        by presence of a corresponding sid/fname key in the data
        """
        sid, fname = self.cache_get_keys(cache, data)
        res = None
        try:
            if fname:
                res = cache[sid].pop(fname)
            else:
                res = cache.pop(sid)
        except KeyError:
            res = None
        return res

    def data_request_stopped(self, data):
        return not self.cache_contains(signal_cache, data)


    async def on_data_request(self, data):
        # print("Data request:", data)

        global datapool
        global signal_cache

        value = data['value']
        filename = value.get('filename', None)
        if filename is None:
            raise ValueError("Received data_request without filename")
        
        # if self.cache_contains(signal_cache, data):
        #     signal_array = self.cache_get(signal_cache, data)
        #     if isinstance(signal_array, ExtendableDataArray):
        #         signal_array = signal_array.data_array.to_dataset()
        # else:
        #     filename_zarr = base_to_zarr_filename(filename, 'signal')
        #     signal_array = open_mfzarr(filename_zarr)
        #     self.cache_put(signal_cache, data, signal_array)
        signal_array = self.cache_get(signal_cache, data)
        if not signal_array:
            filename_zarr = base_to_zarr_filename(filename, 'signal')
            signal_array = open_mfzarr(filename_zarr)
            self.cache_put(signal_cache, data, signal_array)
        if isinstance(signal_array, ExtendableDataArray):
            signal_array = signal_array.data_array.to_dataset()

        set_figure_ranges = False
        mz_range = value.get('mz_range', None)
        t_range = value.get('t_range', None)
        if mz_range is None:
            mz0 = float( signal_array.mz[0] )
            mz1 = float( signal_array.mz[-1] )
            mz_range = [mz0, mz1]
            set_figure_ranges = True
        if t_range is None:
            t0 = float( signal_array.time[0] )
            t1 = float( signal_array.time[-1] )
            t_range = [t0, t1]
            # print(f"t_range: {t_range}")

        signal = signal_array.signal.sel(
                    mz=slice(*mz_range),
                    time=slice(*t_range)
                    )
        mz = signal.mz.values.astype(np.float32)
        t = signal.time.values.astype(np.float32)

        cookies = data['cookies']
        await self.emit_client_notification(
                            'data_stream_coordinates',
                            {'filename': filename,
                             'mz': mz.tobytes(),
                             'time': t.tobytes(),
                             'mz_range': mz_range,
                             't_range': t_range,
                             'set_figure_ranges': set_figure_ranges,
                             },
                            cookies=cookies,
                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                            )
        self.speci = 0
        for i, spec_array in enumerate(signal.transpose()):
            if self.data_request_stopped(data):
                break
            while i - self.speci > 5:
                await asyncio.sleep(.15)
            spec = spec_array.values
            ti = float( spec_array.time )
            await self.emit_client_notification('loaded_spectrum',
                                           {'filename': filename,
                                            'i': i,
                                            'spec': spec.tobytes(),
                                            'mz_range': mz_range,
                                            't_range': t_range,
                                            't': ti,
                                            },
                                           cookies=cookies,
                                           no_data_logging=NO_DATA_LOGGING_DEFAULT,
                                           callback="speci_callback"
                                           )
        self.cache_pop(signal_cache, data)
        await self.emit_client_notification('data_stream_finished',
                                       {'filename': filename,
                                        'mz_range': mz_range,
                                        't_range': t_range,
                                        },
                                       cookies=cookies,
                                       no_data_logging=False
                                       )

    def speci_callback(self, n):
        self.speci = n


    async def on_stop_data_request(self, data):
        global signal_cache
        global tps_cache
        signal_array = self.cache_pop(signal_cache, data)
        if isinstance(signal_array, ExtendableDataArray):
            await signal_array.flush()
        tps_array = self.cache_pop(tps_cache, data)
        if isinstance(tps_array, ExtendableDataArray):
            await tps_array.flush()


    async def on_experiment_selected(self, data):
        value = data['value']
        cookies = data['cookies']
        experiment = value.get('id', '')
        if experiment == '':
            await self.emit_client_notification(
                            'samples',
                            {'rows': [],
                             'cols': [],
                             },
                            cookies=cookies,
                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                            )
            return

        attributes = value.get('attributes')
        project = attributes.get('project')
        global datapool
        if project not in datapool.pool.keys():
            raise ValueError("Requested project does not exist!")

        project_experiments = datapool.pool.get(project).keys()
        # If experiment does not exist, create it
        if experiment not in project_experiments:
            # Create new experiment directory
            datapool.new_experiment(project, experiment, attributes)
            # Update UI
            project_experiments = datapool.get_experiments(project)
            await self.emit_client_notification('experiments',
                                           project_experiments,
                                           cookies=cookies,
                                           no_data_logging=NO_DATA_LOGGING_DEFAULT
                                           )
        # Update sample table data
        await self.emit_client_notification(
                            'samples',
                            datapool.get_sample_table(project, experiment),
                            cookies=cookies,
                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                            )

    async def on_import_sample_table_datetime_range(self, data):
        global datapool
        cookies = data['cookies']
        # Update sample table data
        await self.emit_client_notification(
                            'importable_samples',
                            datapool.get_sample_table(),
                            cookies=cookies,
                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                            )

    async def on_project_selected(self, data):
        global datapool
        value = data['value']
        cookies = data['cookies']
        project = value.get('id', '')
        if project == '':
            await self.emit_client_notification('experiments',
                                        [],
                                        cookies=cookies,
                                        no_data_logging=False)
            return

        attributes = value.get('attributes')
        if project not in datapool.pool.keys():
            print("Starting new project: %s" %project)
            datapool.new_project(project, attributes)
            projects = datapool.get_projects()
            await self.emit_client_notification('projects',
                                        projects,
                                        cookies=cookies,
                                        no_data_logging=NO_DATA_LOGGING_DEFAULT)

        experiments = datapool.get_experiments(project)
        await self.emit_client_notification('experiments',
                                       experiments,
                                       cookies=cookies,
                                       no_data_logging=NO_DATA_LOGGING_DEFAULT)

    async def on_sample_attributes(self, data):
        """Write attributes of a sample to disk. Make a symbolic link from
        the sample directory in 'data_path' to 'project_path'/experiment 

        Parameters
        ----------
        data : [type]
            [description]

        Raises
        ------
        ValueError
            [description]
        """
        global data_path
        global projects_path
        global datapool

        value = data['value']
        sample = value.get('id', '')
        attributes = value.get('attributes')
        if sample == '':
            raise ValueError("Received write_sample_attributes without 'id'")
        project = attributes.get('project', '')
        if project == '':
            raise ValueError("Received write_sample_attributes without 'project'")
        experiment = attributes.get('experiment', '')
        if experiment == '':
            raise ValueError("Received write_sample_attributes without 'experiment'")

        attributes.update({'id': sample})
        datapool.new_sample(project, experiment, sample, attributes)

        # Force experiment update to push sample data to UI
        value['id'] = experiment
        await self.on_experiment_selected({**data, 'name': 'experiment_selected'})

    async def on_tps_data_request(self, data):
        global tps_cache
        
        value = data['value']
        figure_ranges = value.pop('figure_ranges', {})
        filename = figure_ranges.get('filename', None)
        if filename is None:
            raise ValueError("Received data_request without filename")
        
        selected = value.get('tps_parameters_selected', None)
        if selected is None:
            return   
        parameters = [ v.get('label') for _, v in selected.items() ]

        sample_array = self.cache_get(tps_cache, data)
        if not sample_array:
            filename = base_to_zarr_filename(filename, '_tps')
            sample_array = open_mfzarr(filename)
            self.cache_put(tps_cache, data, sample_array)

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

        await self.emit_client_notification(
                            'tps_data_stream_coordinates',
                            {'filename': filename,
                             'parameters': parameters,
                             'time': t.tobytes(),
                             'set_tps_parameters': False,
                             },
                            cookies=data['cookies'],
                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                            )
        self.tps_speci = 0
        for i, param_array in enumerate(tps_data.transpose()):
            if self.data_request_stopped(data):
                break
            while i - self.tps_speci > 5:
                await asyncio.sleep(.15)
            param_ys = param_array.values
            ti = float( param_array.time )
            await self.emit_client_notification('loaded_tps_data',
                                           {'filename': filename,
                                            'i': i,
                                            'tps_data': param_ys.tobytes(),
                                            't': ti,
                                            },
                                           cookies=data['cookies'],
                                           no_data_logging=NO_DATA_LOGGING_DEFAULT,
                                           callback="tps_speci_callback"
                                           )
        self.cache_pop(tps_cache, data)
        await self.emit_client_notification('tps_data_stream_finished',
                                       {'filename': filename},
                                       cookies=data['cookies'],
                                       no_data_logging=False
                                      )
 
    def tps_speci_callback(self, n):
        self.tps_speci = n
   
    # ---------------------------------

    # ========== MS data ==========
    async def on_acquisition_coordinates(self, data):
        """Initialize acquisition cache with received coordinates

        Parameters
        ----------
        data : dict
            keys: 'mz' and 'time'
        """
        global signal_cache

        value = data['value']
        filename_base = value.get('filename')
        print("Start acquiring sample: %s" %filename_base)
        filename = base_to_zarr_filename(filename_base, 'signal')
        
        # Check if sample and dataset with given name exists
        # if os.path.isdir(filename):
        #     print("Dataset %s exists already" %filename)
        #     i = 0
        #     while True:
        #         new_filename_base = filename_base + '_%s' % i
        #         filename = base_to_zarr_filename(new_filename_base, 'signal')
        #         if os.path.isdir(filename):
        #             i += 1
        #             continue
        #         else:
        #             filename_base = new_filename_base
        #             break
        
        print("Writing signal into: %s" %filename)

        mz = np.frombuffer( value.get('mz'), dtype=np.float32 )
        signal_array = ExtendableDataArray(path=filename,
                                           array_module=da
                                           )
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        self.cache_put(signal_cache, data, signal_array)

    async def on_acquired_spectrum(self, data):
        """Receive new spectrum, add to cache

        Parameters
        ----------
        data : dict
            keys: 'filename', 'i', 't' and 'spec'
        """
        global signal_cache

        # Get package index
        value = data['value']
        i = value.get('i')
        print(i)
        filename_base = value.get('filename')

        ti = np.array( [value.get('t')], dtype=np.float32 )
        spec = np.frombuffer(value.get('spec'), dtype=np.float32)
        spec = spec.reshape(-1, 1)
        signal_array = self.cache_get(signal_cache, data)
        mz = signal_array.data_array.mz
        await signal_array.extend_array(spec,
                                        [mz, ti],
                                        'time'
                                        )

    async def on_acquisition_finished(self, data):
        global signal_cache
        global tps_cache

        value = data['value']
        filename_base = value.get('filename')
        filename = base_to_zarr_filename(filename_base, 'signal')
        print("Finished acquiring file: %s" %filename)

        signal_array = self.cache_get(signal_cache, data)
        await signal_array.flush()

        tps_array = self.cache_get(tps_cache, data)
        await tps_array.flush()

    # ------------------------------
    
    # ========== TPS data ==========
    async def on_tps_parameter_info(self, data):
        global tps_cache

        value = data['value']
        filename_base = value.get('filename')
        filename = base_to_zarr_filename(filename_base, 'tps')

        # Check if sample and dataset with given name exists
        # if os.path.isdir(filename):
        #     print("Dataset %s exists already" %filename)
        #     i = 0
        #     while True:
        #         new_filename_base = filename_base + '_%s' % i
        #         filename = base_to_zarr_filename(new_filename_base, 'tps')
        #         if os.path.isdir(filename):
        #             i += 1
        #             continue
        #         else:
        #             filename_base = new_filename_base
        #             break

        print("Writing TPS data into: %s" %filename)

        tps_info = value.get('tps_info')
        
        tps_array = ExtendableDataArray(path=filename,
                                        array_module=da
                                        )
        tps_array.init_array(dims=('parameter', 'time'),
                             coords=[tps_info, []],
                             name='tps'
                             )
        self.cache_put(tps_cache, data, tps_array)

    async def on_acquired_tps_data(self, data):
        global tps_cache
        value = data['value']
        filename_base = value.get('filename')
        ti = np.array( [value.get('t')], dtype=np.float32 )
        tps_data = np.frombuffer( value.get('tps_data'), dtype=np.float32)
        tps_data = tps_data.reshape(-1, 1)
        tps_array = self.cache_get(tps_cache, data)
        tps_info = tps_array.data_array.parameter
        await tps_array.extend_array(tps_data,
                                     [tps_info, ti],
                                     'time'
                                     )
    # ------------------------------

# ---------- Utility functions ----------
def base_to_zarr_filename(base_filename, variable):
    global data_path
    filepath = os.path.join(data_path, base_filename)
    zarr_filename = variable + os.extsep + 'zarr'
    return os.path.join(filepath, zarr_filename)

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


class FileServiceClient(BaseServiceClient):
    pass

def run():
    client = FileServiceClient(*parse_cmd_args(), FileServiceNamespace)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
