# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization.
      
Created on Thu May  7 12:43:13 2020
"""

import asyncio
import json

import numpy as np
from scipy.signal import find_peaks

from karsalib.client import (
                        BaseClientNamespace,
                        BaseServiceClient
                        )
from karsalib.util import parse_datetime_from_item_filename
from karsalib.util import parse_cmd_args, get_client_notification_context

from karsalib.db import SampleManagerDB


from services.FileIoService import load_file

# File cache
cache = {}

NO_DATA_LOGGING_DEFAULT = True

db_path = 'data/samples.db'
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
    
    async def on_workspace_list_request(self, data):
        value = data['value']
        
        await self.emit_client_notification(
            'workspace_rows', db.workspace_list(),
            **{
                **get_client_notification_context(data),
                'client_room': 'workspaces'
            })

    async def on_workspace_create_request(self, data):
        value = data['value']
        
        db.workspace_create(**value)

        await self.emit_client_notification(
            'workspace_rows', db.workspace_list(),
            **{
                **get_client_notification_context(data),
                'client_room': 'workspaces',
            })

    async def on_workspace_update_request(self, data):
        value = data['value']
        
        db.workspace_update(**value)

        await self.emit_client_notification(
            'workspace_rows', db.workspace_list(),
            **{
                **get_client_notification_context(data),
                'client_room': 'workspaces'
            })

    async def on_workspace_delete_request(self, data):
        value = data['value']
        
        db.workspace_delete(id=value.get('id'))

        await self.emit_client_notification(
            'workspace_rows', db.workspace_list(),
            **{
                **get_client_notification_context(data),
                'client_room': 'workspaces'
            })

    # === sample batches === #

    async def on_workspace_sample_batch_list_request(self, data):
        value = data['value']

        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'batch-list',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'batch',
                    'filters': '*',
                    'rows': db.sample_batch_list(
                        workspaceId=value.get('workspaceId')
                    ),
                }
            }, **{
                **get_client_notification_context(data),
               'room': data['client_room']
            })
    
    async def on_workspace_sample_batch_create_request(self, data):
        value = data['value']
        
        db.sample_batch_create(
            id=value.get('id'),
            name=value.get('name'), 
            description=value.get('description'),
            workspaceId=value.get('workspaceId')
            )

        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'batch-create',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'batch',
                    'filters': '*',
                    'rows': db.sample_batch_list(
                        workspaceId=value.get('workspaceId')
                    ),
                }
            }, **{
                **get_client_notification_context(data),
                'room': value.get('workspaceId')
            })

    async def on_workspace_sample_batch_update_request(self, data):
        value = data['value']
        
        db.sample_batch_update(
            id=value.get('id'),
            name=value.get('name'), 
            description=value.get('description')
        )

        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'batch-update',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'batch',
                    'filters': '*',
                    'rows': db.sample_batch_list(
                        value.get('workspaceId')
                    ),
                }
            }, **{
                **get_client_notification_context(data),
                'room': value.get('workspaceId')
            })

    async def on_workspace_sample_batch_delete_request(self, data):
        value = data['value']

        db.sample_batch_delete(
            id=value.get('id')
        )
        
        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'batch-delete',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'batch',
                    'filters': '*',
                    'rows': db.sample_batch_list(
                        value.get('workspaceId')
                    ),
                }
            }, **{
                **get_client_notification_context(data),
                'room': value.get('workspaceId')
            })

    # === sample items === #

    async def on_workspace_sample_item_list_request(self, data):
        value = data['value']
        
        batchId = value.get('id')

        # Update sample table data
        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'item-list',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'item',
                    'filters': {'batchId': batchId},
                    'rows': db.sample_item_list(
                        batchId=batchId
                    ),
                }
            }, **{
                **get_client_notification_context(data),
               'room': data['client_room']
            })

    async def on_workspace_sample_item_create_request(self, data):
        value = data['value']

        batchId = value.get('batchId')

        db.sample_item_create(
            id=value.get('id'),
            batchId=batchId,
            filename=value.get('filename'),
            attributes=value.get('attributes')
        )
        
        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'item-create',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'item',
                    'filters': {'batchId': batchId},
                    'rows': db.sample_item_list(
                        batchId=batchId
                    ),
                }
            }, **{
                **get_client_notification_context(data),
                'room': batchId
            })

    async def on_workspace_sample_item_update_request(self, data):
        value = data['value']

        batchId = value.get('batchId')

        db.sample_item_update(
            id=value.get('id'),
            batchId=value.get('batchId'),
            filename=value.get('filename'),
            attributes=value.get('attributes')
        )
        
        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'item-update',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'item',
                    'filters': {'batchId': batchId},
                    'rows': db.sample_item_list(
                        batchId=batchId
                    ),
                }
            }, **{
                **get_client_notification_context(data),
                'room': batchId
            })

    async def on_workspace_sample_item_delete_request(self, data):
        ''' Remove sample item from a sample batch '''
        value = data['value']

        batchId = value.get('batchId')

        db.sample_item_delete(
            id=value.get('id')
        )

        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'item-delete',
                'requestId': value['requestId'],
                'payload': {
                    'level': 'item',
                    'filters': {'batchId': batchId},
                    'rows': db.sample_item_list(
                        batchId=batchId
                    ),
                }
            }, **{
                **get_client_notification_context(data),
                'room': batchId
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
            dt = parse_datetime_from_item_filename(filename)
            db.sample_file_insert(
                filename=filename,
                instrument=filename.split('_')[0],
                datetime=dt.isoformat(),
                length=committed_length,
                range=json.dumps(value['mz_range'])
            )

    # peaks

    async def on_workspace_sample_peak_list_request(self, data):
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

        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'peak-list',
                'requestId': value['requestId'],
                'payload': {
                    'sampleItemId': value['sampleItemId'],
                    'mzsBytes': peak_mzs_bytes,
                    'heightsBytes': peak_heights_bytes,
                    'tofsBytes': peak_tofs_bytes
                }
            },
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
