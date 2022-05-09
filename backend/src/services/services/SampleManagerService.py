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
from datetime import timedelta

import numpy as np
from scipy.signal import find_peaks

from karsalib.client import (
                        BaseClientNamespace,
                        BaseServiceClient
                        )
from karsalib.util import parse_datetime_from_item_filename
from karsalib.util import parse_cmd_args, get_client_notification_context
from karsalib.db import SampleManagerDB, gen_id

from services.FileIoService import load_file

# File cache
cache = {}

NO_DATA_LOGGING_DEFAULT = True

data_path = os.environ.get('MASCOPE_DATADIR', '.')
db_path = os.path.join(data_path, 'samples.db')
db = SampleManagerDB(db_path)


class SampleServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    service_state = dict(
        workspace_rows = {
            'value': db.workspace_read(),
            'room': 'workspaces'
        },
    )

    # ========== UI requests ==========

    # === workspaces === #
    
    async def on_workspace_create_request(self, data):
        workspaces = [
            {'id': gen_id(), **workspace}
            for workspace in data['value']
        ]
        for workspace in workspaces:        
            db.workspace_create(**workspace)
        return {
            'type': 'success',
            'body': workspaces
        }

    async def on_workspace_read_request(self, data):
        workspaces = db.workspace_read()
        return {
            'type': 'success',
            'body': workspaces
        }

    async def on_workspace_update_request(self, data):
        workspaces = data['value']
        for workspace in workspaces:
            db.workspace_update(**workspace)
        return {
            'type': 'success',
            'body': None
        }

    async def on_workspace_delete_request(self, data):
        workspace_ids = [
            workspace['id']
            for workspace in data['value']
        ]
        for workspace_id in workspace_ids:
            db.workspace_delete(id=workspace_id)
        return {
            'type': 'success',
            'body': None
        }

    # === sample batches === #

    async def on_sample_batch_create_request(self, data):
        batches = [
            {'id': gen_id(), **batch}
            for batch in data['value']
        ]
        for batch in batches:
            db.sample_batch_create(**batch)
        return {
            'type': 'success',
            'body': batches
        }

    async def on_sample_batch_read_request(self, data):
        filters = data['value']
        batches = db.sample_batch_read(**filters)
        return {
            'type': 'success',
            'body': batches
        }
    
    async def on_sample_batch_update_request(self, data):
        batches = data['value']
        for batch in batches:
            db.sample_batch_update(**batch)
        return {
            'type': 'success',
            'body': None
        }

    async def on_sample_batch_delete_request(self, data):
        batch_ids = data['value']
        item_ids = []
        for batch_id in batch_ids:
            # delete the batch record
            db.sample_batch_delete(id=batch_id)
            # delete associated item records
            items = db.sample_item_read(batchId=batch_id)
            for item in items:
                item_id = item['id']
                db.sample_item_delete(id=item_id)
                item_ids.push(item_id)
        return {
            'type': 'success',
            'body': {
                'batches': batch_ids,
                'items': item_ids
            }
        }

    # === sample items === #

    async def on_sample_item_create_request(self, data):
        items = [
            {
                'id': gen_id(),
                **item,
                'attributes': json.dumps(item['attributes'])
            }
            for item in data['value']
        ]
        for item in items:
            db.sample_item_create(**item)
        return {
            'type': 'success',
            'body': items
        }

    async def on_sample_item_read_request(self, data):
        filters = data['value']
        items = db.sample_item_read(**filters)
        return {
            'type': 'success',
            'body': items
        }

    async def on_sample_item_update_request(self, data):
        items = data['value']
        for item in items:
            db.sample_item_update(**item)
        return {
            'type': 'success',
            'body': None
        }
    
    async def on_sample_item_delete_request(self, data):
        item_ids = data['value']
        for item_id in item_ids:
            db.sample_item_delete(id=item_id)
        return {
            'type': 'success',
            'body': None
        }

    async def on_sample_item_schema_request(self, data):
        # data: {field_name: field_value}
        timeout = data.get('timeout')
        context = get_client_notification_context(data)
        schema = db.sample_item_get_schema()
        result = {'schema': schema, 'dummy': time()}     # ensure response accepted, when schema not changed
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


    # === sample files === #

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
            record['attributes'] = json.loads(record.get('attributes') or '[]')
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
        result = {'schema': schema, 'dummy': time()}     # ensure response accepted, when schema not changed
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

    async def on_dataset_updated(self, data):
        value = data['value']
        if value['data_type'] != 'signal':
            raise ValueError(f"Expected data_type: signal - got {value['data_type']}")
        filename = value['filename']
        full_length = value['length']
        committed_length = value['committed_length']
        if committed_length >= full_length:
            # update sample store
            instrument = filename.split('_')[0]
            dt = parse_datetime_from_item_filename(filename)
            title = value.get('title', "")
            utc_offset = timedelta(seconds=int(value['utc_offset']))
            db.sample_file_insert(
                id=filename,
                filename=filename,
                instrument=instrument,
                title=title,
                datetime=dt.isoformat(),
                datetime_utc=(dt - utc_offset).isoformat(),
                length=committed_length,
                range=json.dumps(value['range'])
            )

    # === templates === #

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
