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
from karsatof.kdatapool import SamplePool
from karsatof.kimage import (convert_base64_to_img, convert_to_base64)


NO_DATA_LOGGING_DEFAULT = True

projects_path = 'Projects' # TODO: make configurable
datapool = SamplePool(projects_path)

class MetadataServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    endpoints = [
        # DataViz
        'stop_data_request',
        # UI
        'experiment_selected',
        'delete_experiment',
        'delete_project',
        'delete_sample',
        'import_sample_table_datetime_range', # TODO: Should be routed to FileIoService
        'project_selected',
        'projects',
        'save_experiment',
        'save_project',
        'save_sample',
        'save_sample_annotation',
        # Router
        'service_state',
        ]

    service_state = dict(
        projects = datapool.get_projects(),
    )

    # ========== DataViz requests ========== 
    async def on_stop_data_request(self, data):
        try:
            namespace = '/' + data['value']['filename'].split('_')[0]
        except KeyError as e:
            # TODO: Should not end up here
            self.log(e)
            # Do not know where to forward it, return
            return
        value = data['value']
        kwargs = get_client_notification_args(data)

        await self.emit_client_notification('stop_data_request',
                                            value,
                                            **kwargs,
                                            namespace=namespace
                                            )

    # ========== UI requests ==========
    async def on_experiment_selected(self, data):
        value = data['value']
        self.log(value)
        kwargs = get_client_notification_args(data)
        experiment = value.get('title')
        project = value.get('project')

        global datapool
        if project not in datapool.pool.keys():
            raise ValueError("Requested project does not exist!")
        project_experiments = datapool.pool.get(project).keys()
        if experiment not in project_experiments:
            raise ValueError("Requested experiment does not exist!")
        # Update sample table data
        await self.emit_client_notification(
                            'samples',
                            datapool.get_samples(project, experiment),
                            room=data['client_room']
                            )

    async def on_import_sample_table_datetime_range(self, data):
        global datapool
        # Update sample table data
        await self.emit_client_notification(
                            'importable_samples',
                            datapool.get_samples(),
                            **{**get_client_notification_args(data),
                               'room': data['client_room']
                               }
                            )

    async def on_project_selected(self, data):
        global datapool
        value = data['value']
        kwargs = get_client_notification_args(data)
        project = value.get('title')

        if project not in datapool.pool.keys():
            raise ValueError("Requested project does not exist!")

        experiments = datapool.get_experiments(project)
        await self.emit_client_notification(
                                    'experiments',
                                    experiments,
                                    room=data['client_room'],
                                    )
    
    async def on_delete_experiment(self, data):
        global datapool
        self.log(data)
        value = data['value']
        experiment = value['experiment']
        project = value['project']

        datapool.delete_experiment(project, experiment)
        
        project_experiments = datapool.get_experiments(project)
        await self.emit_client_notification(
                        'experiments',
                        project_experiments,
                        room=project,
                        )

    async def on_delete_project(self, data):
        global datapool
        self.log(data)
        value = data['value']
        project = value['project']

        datapool.delete_project(project)

        projects = datapool.get_projects()
        await self.emit_client_notification(
                                    'projects',
                                    projects,
                                    )

    async def on_delete_sample(self, data):
        ''' Remove sample from an experiment '''
        global datapool
        value = data['value']
        filename = value['filename']
        experiment = value['experiment']
        project = value['project']
        datapool.delete_sample(project, experiment, filename)
        # Update sample table data in UIs
        await self.emit_client_notification(
                            'samples',
                            datapool.get_samples(project, experiment),
                            room='_'.join([project, experiment])
                            )

    async def on_save_experiment(self, data):
        value = data['value']
        self.log(value)
        experiment = value.get('title')
        project = value.get('project')
        attributes = value.get('attributes')
        sample_attributes_template = value.get('sample_attributes_template')
        # Create new experiment directory

        if project not in datapool.pool.keys():
            raise ValueError("Requested project does not exist!")
        project_experiments = datapool.pool.get(project).keys()
        if experiment not in project_experiments:
            # New experiment
            datapool.new_experiment(project,
                                    experiment,
                                    attributes,
                                    sample_attributes_template
                                    )
        else:
            # Edit existing experiment
            datapool.edit_experiment(project,
                                     experiment,
                                     attributes,
                                     )

        project_experiments = datapool.get_experiments(project)
        await self.emit_client_notification(
                        'experiments',
                        project_experiments,
                        room=project,
                        )

    async def on_save_project(self, data):
        value = data['value']
        self.log(value)
        project = value.get('title')
        attributes = value.get('attributes')

        if project not in datapool.pool.keys():
            # New project
            datapool.new_project(project, attributes)
        else:
            # Edit existing project
            datapool.edit_project(project, attributes)
        
        projects = datapool.get_projects()
        await self.emit_client_notification(
                                    'projects',
                                    projects,
                                    )

    async def on_save_sample(self, data):
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
        self.log(value)
        filename = value['filename']
        experiment = value['experiment']
        project = value['project']
        attributes = value.get('attributes')

        try:
            samples = datapool.pool.get(project).get(experiment)
        except KeyError:
            raise ValueError("Requested project or experiment does not exist!")
        if filename not in samples:
            # New sample attributes
            datapool.new_sample(project, experiment, filename, attributes)
        else:
            # Edit sample attributes
            datapool.edit_sample(project, experiment, filename, attributes)

        # Update sample table data in UIs
        await self.emit_client_notification(
                            'samples',
                            datapool.get_samples(project, experiment),
                            room='_'.join([project, experiment])
                            )
    
    async def on_save_sample_annotation(self, data):
        global datapool

        value = data['value']
        filename = value['filename']
        project = value['project']
        experiment = value['experiment']
        annotation = value['annotation']

        datapool.annotate_sample(project, experiment, filename, annotation)
    # ---------------------------------


class SampleManagerClient(BaseServiceClient):
    pass


def run():
    global projects_path

    args = parse_cmd_args()
    client = SampleManagerClient(args['url'],
                                 args['port'],
                                 (args['ns'], MetadataServiceNamespace)
                                 )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
