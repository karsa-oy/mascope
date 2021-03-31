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
        'data_request',
        'image_to_save',
        'stop_data_request',
        # UI
        'experiment_selected',
        'experiments',
        'import_sample_table_datetime_range', # TODO: Should be routed to FileIoService
        'project_selected',
        'projects',
        'sample_attributes',
        # Router
        'service_state',
        ]

    service_state = dict(
        projects = datapool.get_projects(),
    )

    # ========== DataViz requests ========== 
    async def on_data_request(self, data):
        namespace = '/' + data['value']['filename'].split('_')[0]
        value = data['value']
        kwargs = get_client_notification_args(data)

        await self.emit_client_notification('data_request',
                                            value,
                                            **kwargs,
                                            namespace=namespace
                                            )

    async def on_image_to_save(self, data):
        namespace = '/' + data['value']['filename'].split('_')[0]
        value = data['value']
        kwargs = get_client_notification_args(data)

        await self.emit_client_notification('image_to_save',
                                            value,
                                            **{**kwargs,
                                               'namespace': namespace
                                               }
                                            )

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
        kwargs = get_client_notification_args(data)
        experiment = value.get('id')
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
            await self.emit_client_notification(
                            'experiments',
                            project_experiments,
                            room=project,
                            )
        # Update sample table data
        await self.emit_client_notification(
                            'samples',
                            datapool.get_sample_table(project, experiment),
                            **{**kwargs,
                               'room': data['client_room']
                                }
                            )

    async def on_import_sample_table_datetime_range(self, data):
        global datapool
        # Update sample table data
        await self.emit_client_notification(
                            'importable_samples',
                            datapool.get_sample_table(),
                            **{**get_client_notification_args(data),
                               'room': data['client_room']
                               }
                            )

    async def on_project_selected(self, data):
        global datapool
        value = data['value']
        kwargs = get_client_notification_args(data)
        project = value.get('id')

        if project not in datapool.pool.keys():
            # New project
            attributes = value.get('attributes')
            datapool.new_project(project, attributes)
            projects = datapool.get_projects()
            await self.emit_client_notification(
                                    'projects',
                                    projects,
                                    **{**kwargs,
                                       'room': data['client_room']
                                        }
                                    )

        experiments = datapool.get_experiments(project)
        await self.emit_client_notification(
                                    'experiments',
                                    experiments,
                                    **{**kwargs,
                                       'room': data['client_room']
                                        }
                                    )

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
        sample = value['id']
        attributes = value.get('attributes')
        project = attributes['project']
        experiment = attributes['experiment']

        if not attributes.get('remove'):
            # Update (or create) sample attributes
            attributes.update({'id': sample})
            datapool.new_sample(project, experiment, sample, attributes)
        else:
            # Remove sample (link from experiment)
            datapool.delete_sample(project, experiment, sample)

        # Update sample table data in UIs
        await self.emit_client_notification(
                            'samples',
                            datapool.get_sample_table(project, experiment),
                            **{**get_client_notification_args(data),
                               'room': '_'.join([project, experiment])
                               }
                            )
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
