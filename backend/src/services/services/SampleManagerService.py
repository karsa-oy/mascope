# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization.
      
Created on Thu May  7 12:43:13 2020
"""

import asyncio
import os
import json
from time import time

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

data_path = os.environ.get('MASCOPE_DATADIR')
db_path = os.path.join(data_path, 'samples.db')
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

    async def on_sample_batch_list_request(self, data):
        value = data['value']

        await self.emit_client_notification(
            'sample_response', {
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
    
    async def on_sample_batch_create_request(self, data):
        value = data['value']
        
        db.sample_batch_create(
            id=value.get('id'),
            name=value.get('name'), 
            description=value.get('description'),
            workspaceId=value.get('workspaceId')
            )

        await self.emit_client_notification(
            'sample_response', {
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

    async def on_sample_batch_update_request(self, data):
        value = data['value']
        
        db.sample_batch_update(
            id=value.get('id'),
            name=value.get('name'), 
            description=value.get('description')
        )

        await self.emit_client_notification(
            'sample_response', {
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

    async def on_sample_batch_delete_request(self, data):
        value = data['value']

        db.sample_batch_delete(
            id=value.get('id')
        )
        
        await self.emit_client_notification(
            'sample_response', {
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

    async def on_sample_item_list_request(self, data):
        value = data['value']
        
        batchId = value.get('id')

        # Update sample table data
        await self.emit_client_notification(
            'sample_response', {
                'type': 'item-list',
                'requestId': value.get('requestId', time()),  # ensure response generated, when data not changed
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

    async def on_sample_item_create_request(self, data):
        value = data['value']

        batchId = value.get('batchId')

        db.sample_item_create(
            id=value.get('id'),
            batchId=batchId,
            filename=value.get('filename'),
            attributes=value.get('attributes')
        )
        
        await self.emit_client_notification(
            'sample_response', {
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

    async def on_sample_item_update_request(self, data):
        value = data['value']

        batchId = value.get('batchId')

        db.sample_item_update(
            id=value.get('id'),
            batchId=value.get('batchId'),
            filename=value.get('filename'),
            attributes=value.get('attributes')
        )
        
        await self.emit_client_notification(
            'sample_response', {
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

    async def on_sample_item_delete_request(self, data):
        ''' Remove sample item from a sample batch '''
        value = data['value']

        batchId = value.get('batchId')

        db.sample_item_delete(
            id=value.get('id')
        )

        await self.emit_client_notification(
            'sample_response', {
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

    # template table handlers

    async def on_template_list_request(self, data):
        # templates = [
        #     {"name":"template_1","type":"sample","template":'[{"label":"fname","required":true,"placeholder":"fname"},{"label":"description","value":"Predefined description"},{"label":"optional attribute"}]'},
        #     ...,
        # ]
        templateType = data['value']['type']
        context = get_client_notification_context(data)
        timeout = context.get('timeout')
        records = db.attribute_template_get(type=templateType)
        for r in records:
            r['template'] = json.loads(r['template'])
        if timeout:
            # return code for (backend) clients, which can use call instead of emit
            return records
        else:
            # notification for clients, which prefer callbacks
            await self.emit_client_notification(
                'template_list_response',
                records,
                **{
                    **context,
                    'room': data.get('client_room'),
                })

    async def on_template_save(self, data):
        value = data['value']
        template = {
            'name': value['name'],
            'type': value.get('type', 'unknown'),
            'template': json.dumps(value['template']),
        }
        db.attribute_template_insert(**template)

    async def on_template_delete(self, data):
        template_id = data['value']['id']
        db.attribute_template_delete(template_id)

    async def on_sample_file_update_request(self, data):
        # data[value]: {key: value, ...}
        row = data['value']
        schema_fields = [title for title,*_ in db.sample_files.schema]
        result = {}
        attribs = {}
        for key, val in row.items():
            if key in schema_fields:
                result[key] = val
            else:
                attribs[key] = val
        result['attributes'] = json.dumps({**row.get('attributes', {}), **attribs})
        # keep existing unmentioned fields intact
        the_rows = db.sample_file_get(id=row['id'])
        the_row = {} if not the_rows else the_rows[0]
        db.sample_file_insert(**{**the_row,**result})


    async def on_sample_item_update_request(self, data):
        # data[value]: [{key:value, ...}, ...]
        def save_single_item_data(row):
            schema_fields = [title for title,*_ in db.sample_items.schema]
            result = {}
            attribs = {}
            for key, val in row.items():
                if key in schema_fields:
                    result[key] = val
                else:
                    attribs[key] = val
            result['attributes'] = json.dumps({**row.get('attributes', {}), **attribs})
            # keep existing unmentioned fields intact
            the_rows = db.sample_item_get(title=row['title'], batchId=row['batchId'])
            the_row = {} if not the_rows else the_rows[0]
            if the_row:     # if item exists, skip incoming id to use the existing one
                result.pop('id')
            db.sample_item_insert(**{**the_row,**result})

        rows = data['value']
        batch_ids = []
        for row in rows:
            save_single_item_data(row)
            batch_ids.append(row['batchId'])

        # TODO: refresh batch views - move the call to UI after fixing sync notifications
        for id in batch_ids:
            reload_batch_data = {
                'name': 'sample_item_list_request',
                'value': {'id': id},
                **{
                    **get_client_notification_context(data),
                    'room': id,
                  },
            }
            await self.on_sample_item_list_request(reload_batch_data)


    async def on_sample_file_list_request(self, data):
        # data: {field_name: field_value}
        timeout = data.get('timeout')
        context = get_client_notification_context(data)
        value = data['value']

        if sorted(value.keys()) == sorted(['column', 'min_value', 'max_value']):
            records = db.sample_file_get_range(**value)
        else:
            records = db.sample_file_get(**value)
        for record in records:
            record['attributes'] = json.loads(record['attributes'])
        result = {'records': records, 'dummy': time()}  # ensure response generated, when data not changed
        if timeout:
            return result
        else:
            await self.emit_client_notification(
                'sample_file_list_response',
                result,
                **{
                    **context,
                    'room': data.get('client_room'),
                })

    async def on_sample_file_schema_request(self, data):
        # data: {field_name: field_value}
        timeout = data.get('timeout')
        context = get_client_notification_context(data)
        schema = db.sample_file_get_schema()
        result = {'schema': schema, 'dummy': time()}     # ensure response generated, when schema not changed
        if timeout:
            return result
        else:
            await self.emit_client_notification(
                'sample_file_schema_response',
                result,
                **{
                    **context,
                    'room': data.get('client_room'),
                })

    async def on_sample_item_schema_request(self, data):
        # data: {field_name: field_value}
        timeout = data.get('timeout')
        context = get_client_notification_context(data)
        schema = db.sample_item_get_schema()
        result = {'schema': schema, 'dummy': time()}     # ensure response generated, when schema not changed
        if timeout:
            return result
        else:
            await self.emit_client_notification(
                'sample_item_schema_response',
                result,
                **{
                    **context,
                    'room': data.get('client_room'),
                })



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
