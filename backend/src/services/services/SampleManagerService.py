# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization.
      
Created on Thu May  7 12:43:13 2020
"""

import asyncio
import csv
import os
import tempfile
import random

import numpy as np
from scipy.signal import find_peaks

from karsalib.client import (
                        BaseClientNamespace,
                        BaseServiceClient
                        )
from karsalib.util import parse_cmd_args, get_client_notification_context

from karsalib.db import SampleManagerDB
from karsalib.datapool import SampleCatalog
#from karsaHT3000A.ht3000a import parse_csv_report, dup_cycles


from services.FileIoService import load_file

# File cache
cache = {}

NO_DATA_LOGGING_DEFAULT = True

workspace_path = 'workspaces' # TODO: make configurable
# datapool = SampleCatalog(workspace_path)

# db_path = ':memory:'
db_path = 'samples.db'
db = SampleManagerDB(db_path)


class SampleServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    service_state = dict(
        workspace_rows = {
            'value': db.workspace_list(),
            'room': 'workspaces'
        },
    )

    # ========== UI requests ==========

    # === workspaces === #
    
    # async def on_workspace_save_request(self, data):
    #     value = data['value']

    #     workspace_id = value.get('id')
    #     attributes = value.get('attributes')
    #     attributes.update({'id': workspace_id})
    #     kwargs = get_client_notification_context(data)

    #     self.log(workspace_id)
    #     self.log(datapool.pool.keys())

    #     if workspace_id not in datapool.pool.keys():
    #         # New workspace
    #         datapool.new_workspace(workspace_id, attributes)
    #     else:
    #         # Edit existing workspace
    #         datapool.edit_workspace(workspace_id, attributes)

    #     # sync sample db
    #     self.parent.db.catalog_mkdir('/'.join(['', workspace_id])) 
        
    #     workspace_rows = datapool.get_workspaces()
    #     await self.emit_client_notification(
    #                                 'workspace_rows',
    #                                 workspace_rows,
    #                                 **{**kwargs,
    #                                     'client_room': 'workspaces'
    #                                 })
    async def on_workspace_save_request(self, data):
        value = data['value']
        kwargs = get_client_notification_context(data)

        db.workspace_create(**value)
        
        workspace_rows = db.workspace_list()

        await self.emit_client_notification(
                                    'workspace_rows',
                                    workspace_rows,
                                    **{**kwargs,
                                        'client_room': 'workspaces'
                                    })

    async def on_workspace_delete_request(self, data):
        value = data['value']

        workspace_id = value['id']
        kwargs = get_client_notification_context(data)

        datapool.delete_workspace(workspace_id)

        # sync sample db
        self.parent.db.catalog_remove('/'.join(['', workspace_id]))

        workspace_rows = datapool.get_workspaces()
        await self.emit_client_notification(
                                    'workspace_rows',
                                    workspace_rows,
                                    **kwargs,
                                    )

    # === sample batches === #

    async def on_workspace_sample_batch_fetch_request(self, data):
        value = data['value']

        workspace_id = value.get('id')
        kwargs = get_client_notification_context(data)

        if workspace_id not in datapool.pool.keys():
            raise ValueError("Requested workspace does not exist!")

        workspace_sample_update = {
            'type': 'batch-fetch',
            'requestId': value['requestId'],
            'payload': {
                'level': 'batch',
                'filters': '*',
                'rows': datapool.get_batches(workspace_id),
            }
        }
        await self.emit_client_notification(
                                    'workspace_sample_update',
                                    workspace_sample_update,
                                    **{**kwargs,
                                       'room': data['client_room']
                                      },
                                )
    
    async def on_workspace_sample_batch_save_request(self, data):
        value = data['value']
        
        workspace_id = value.get('workspaceId')
        batch_id = value.get('id')
        attributes = value.get('attributes')
        item_placeholders = value.get('item_placeholders', [])
        kwargs = get_client_notification_context(data)

        # Create new batch directory
        if workspace_id not in datapool.pool.keys():
            raise ValueError("Requested workspace does not exist!")
        batch_ids = datapool.pool.get(workspace_id).keys()
        if batch_id not in batch_ids:
            # New batch
            datapool.new_batch(workspace_id,
                               batch_id,
                               attributes
                               )
        else:
            # Edit batch
            datapool.edit_batch(workspace_id,
                                batch_id,
                                attributes,
                                )

        # sync sample db
        self.parent.db.catalog_mkdir('/'.join(['', workspace_id, batch_id]))

        # Create placeholders for each sample
        for i, item_placeholder in enumerate(item_placeholders):
            placeholder = '%03d_placeholder' %(i+1)
            datapool.new_item(workspace_id,
                              batch_id,
                              placeholder,
                              item_placeholder.get('attributes', []),
                              placeholder=True
                              )

        workspace_sample_update = {
            'type': 'batch-save',
            'requestId': value['requestId'],
            'payload': {
                'level': 'batch',
                'filters': '*',
                'rows': datapool.get_batches(workspace_id),
            }
        }
        await self.emit_client_notification(
                        'workspace_sample_update',
                        workspace_sample_update,
                        **{**kwargs,
                            'room': workspace_id
                        })

    async def on_workspace_sample_batch_delete_request(self, data):
        value = data['value']
        self.log(data)

        workspace_id = value['workspaceId']
        batch_id = value['id']
        kwargs = get_client_notification_context(data)

        datapool.delete_batch(workspace_id, batch_id)

        # sync sample db
        self.parent.db.catalog_remove('/'.join(['', workspace_id, batch_id]))
        
        workspace_sample_update = {
            'type': 'batch-delete',
            'requestId': value['requestId'],
            'payload': {
                'level': 'batch',
                'filters': '*',
                'rows': datapool.get_batches(workspace_id),
            }
        }
        await self.emit_client_notification(
                        'workspace_sample_update',
                        workspace_sample_update,
                        **{**kwargs,
                            'room': workspace_id
                        })


    # === sample items === #

    async def on_workspace_sample_item_fetch_request(self, data):
        value = data['value']
        
        workspace_id = value.get('workspaceId')
        batch_id = value.get('id')
        kwargs = get_client_notification_context(data)

        # Update sample table data
        workspace_sample_update = {
            'type': 'item-fetch',
            'requestId': value['requestId'],
            'payload': {
                'level': 'item',
                'filters': {'batchId': batch_id},
                'rows': datapool.get_items(workspace_id, batch_id),
            }
        }
        await self.emit_client_notification(
                            'workspace_sample_update',
                            workspace_sample_update,
                            **{**kwargs,
                               'room': data['client_room']
                            })

    async def on_workspace_sample_item_save_request(self, data):
        """Write attributes of a sample item to disk. Make a symbolic link 
        from the sample directory in 'data_path' to 'workspace_id/batch_id' 
        path.

        Parameters
        ----------
        data : [type]
            [description]

        Raises
        ------
        ValueError
            [description]
        """
        value = data['value']

        workspace_id = value['workspaceId']
        batch_id = value['batchId']
        item_id = value['id']
        attributes = value.get('attributes')
        kwargs = get_client_notification_context(data)

        try:
            item_ids = datapool.pool.get(workspace_id).get(batch_id)
        except KeyError:
            raise ValueError("Requested workspace or batch does not exist!")
        if item_id not in item_ids:
            # New sample attributes
            datapool.new_item(workspace_id, batch_id, item_id, attributes)
        else:
            # Edit sample attributes
            datapool.edit_item(workspace_id, batch_id, item_id, attributes)

        # sync sample db
        self.parent.db.catalog_add('/'.join(['', workspace_id, batch_id, item_id]), item_id)

        # Update sample table data in UIs
        workspace_sample_update = {
            'type': 'item-save',
            'requestId': value['requestId'],
            'payload': {
                'level': 'item',
                'filters': {'batchId': batch_id},
                'rows': datapool.get_items(workspace_id, batch_id),
            }
        }
        await self.emit_client_notification(
                            'workspace_sample_update',
                            workspace_sample_update,
                            **{**kwargs,
                                'room': workspace_id + batch_id
                            })

    async def on_workspace_sample_item_delete_request(self, data):
        ''' Remove sample item from a sample batch '''
        value = data['value']

        workspace_id = value['workspaceId']
        batch_id = value['batchId']
        filename = value['filename']
        kwargs = get_client_notification_context(data)
        
        try:
            datapool.delete_sample(workspace_id, batch_id, filename)
        except Exception as e:
            self.log('Error:', str(e))
        
        # Update sample table data in UIs
        workspace_sample_update = {
            'type': 'item-delete',
            'requestId': value['requestId'],
            'payload' : {
                'level': 'item',
                'filters': {'batchId': batch_id},
                'rows': datapool.get_items(workspace_id, batch_id),
            }
        }
        await self.emit_client_notification(
                            'workspace_sample_update',
                            workspace_sample_update,
                            **{**kwargs,
                                'room': workspace_id + batch_id
                            })

    # sample db

    async def on_dataset_updated(self, data):
        value = data['value']
        if value['data_type'] != 'signal':
            raise ValueError(f"Expected data_type: signal - got {value['data_type']}")
        filename = value['filename']
        full_length = value['length']
        committed_length = value['committed_length']
        if committed_length >= full_length:
            # update sample store
            datetime, date, time = get_date_time_from_sample_name(filename)
            sample_store_data = {
                'filename': filename,
                'instrument': filename.split('_')[0],
                'date': date,
                'time': time,
                'length': committed_length,
            }
            self.parent.db.sample_file_insert(**sample_store_data)

    # peaks

    async def on_workspace_sample_peak_request(self, data):
        value = data['value']
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        filename = value['filename']
        mz_range = value.get('mzRange')
        t_range = value.get('tRange')
        peak_threshold = value.get('minPeakIntensity')*1e-5 # [%]
        min_peak_distance = value.get('minPeakSeparation')
        min_peak_width = value.get('minPeakWidth')

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename, vars=['signal']) #vars=['centroids', 'signal'])
            cache[filename] = cache_item

        # default to full ranges if none is provided
        if mz_range is None:
            mz_range = cache_item.attrs['props']['range']
        if t_range is None:
            t_range = [0, cache_item.attrs['props']['length']]

        # slice the spectrum and compute min peak height
        sum_spectrum = cache_item.signal.sel(
                            mz=slice(*mz_range),
                            time=slice(*t_range)
                            ).sum(dim='time').compute()
        min_peak_height = peak_threshold * sum_spectrum.max().compute().item()

        # find peaks in the spectrum
        peak_indeces, peak_props = find_peaks(sum_spectrum,
                                        height=min_peak_height,
                                        distance=min_peak_distance,
                                        width=min_peak_width
                                        )

        # abort if peak limit exceeded
        MAX_NO_PEAKS = 20000
        if len(peak_indeces) > MAX_NO_PEAKS:
            await self.parent.push_log.error(
                        "Warning! Max number of peaks exceeded: %s. Peak data omitted." %len(peak_mzs_bytes),
                        room=client_room,
                        namespace='/'
                        )
            return

        # export peaks
        export = lambda vals : vals.astype(np.float32).tobytes()
        peak_mzs_bytes = export(sum_spectrum.mz[peak_indeces].values)
        peak_heights_bytes = export(peak_props['peak_heights'])
        peak_tofs_bytes = export(peak_indeces)

        workspace_sample_update = { 
            'type': 'peak-fetch',
            'requestId': value['requestId'],
            'payload': {
                'sampleItemId': value['sampleItemId'],
                'mzsBytes': peak_mzs_bytes,
                'heightsBytes': peak_heights_bytes,
                'tofsBytes': peak_tofs_bytes
            }
        }

        self.log(workspace_sample_update)

        await self.emit_client_notification('workspace_sample_update',
                                            workspace_sample_update,
                                            room=client_room
                                            )





class SampleManagerClient(BaseServiceClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def run():
    args = parse_cmd_args()
    client = SampleManagerClient(args['url'],
                                 args['port'],
                                 (args['ns'], SampleServiceNamespace)
                                 )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt as e:
        print(f"{client.__class__.__name__} : {e.__class__.__name__}({str(e)})")
    except Exception as e:
        print(f"{client.__class__.__name__} : {e.__class__.__name__}({str(e)})")
    finally:
        client.shutdown_event.set()
        print(f'Service stopped.')



if __name__=='__main__':
    run()
