# -*- coding: utf-8 -*-
"""File Service

This script runs the file service for Karsa Tarkka TOF system.

FileService connects to the :mod:`~router_service.router_service.Router`
via socket.io, and handles file i/o synchronization.
      
Created on Thu May  7 12:43:13 2020
"""

import asyncio
from time import time
from datetime import timedelta

from karsalib.client import (
                        BaseClientNamespace,
                        BaseServiceClient
                        )
from karsalib.util import (
    parse_datetime_from_item_filename,
    parse_cmd_args,
    get_client_notification_context,
    map_to_snake_case,
    map_to_camel_case
)
from karsalib.db import DbInstance, gen_id, get_ids

# File cache
cache = {}

NO_DATA_LOGGING_DEFAULT = True

db = DbInstance()


class SampleServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    # ========== UI requests ==========

    # === workspaces === #

    async def on_workspace_create_request(self, data):
        workspaces = [
            {**workspace, 'id': gen_id()}
            for workspace in map_to_snake_case(
                data['value']
            )
        ]
        for workspace in workspaces:
            db.workspace_create(**workspace)
        workspace_ids = get_ids(workspaces)
        await self.notify(
            'workspace_event', {'type': 'create', 'ids': workspace_ids},
            **{
                **get_client_notification_context(data),
                'room': 'workspace',
            }
        )
        return {
            'type': 'success',
            'body': workspace_ids
        }

    async def on_workspace_read_request(self, data):
        filters = map_to_snake_case(
            data.get('value', {})
        )
        workspaces = db.workspace_read(**filters)
        return {
            'type': 'success',
            'body': map_to_camel_case(
                workspaces
            )
        }

    async def on_workspace_update_request(self, data):
        workspaces = map_to_snake_case(
            data['value']
        )
        for workspace in workspaces:
            db.workspace_update(**workspace)
        workspace_ids = get_ids(workspaces)
        await self.notify(
            'workspace_event', {'type': 'update', 'ids': workspace_ids},
            **{
                **get_client_notification_context(data),
                'room': 'workspace',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    async def on_workspace_delete_request(self, data):
        workspace_ids = data['value']
        batch_ids = get_ids(
            db.sample_batch_read(workspace_id=workspace_ids)
        )
        db.workspace_delete(id=workspace_ids)
        self.on_sample_batch_delete_request(batch_ids)
        await self.notify(
            'workspace_event', {'type': 'delete', 'ids': workspace_ids},
            **{
                **get_client_notification_context(data),
                'room': 'workspace',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    # === sample batches === #

    async def on_sample_batch_create_request(self, data):
        batches = [
            {'id': gen_id(), **batch}
            for batch in map_to_snake_case(
                data['value']
            )
        ]
        for batch in batches:
            db.sample_batch_create(**batch)
        batch_ids = get_ids(batches)
        await self.notify(
            'sample_batch_event', {'type': 'create', 'ids': batch_ids},
            **{
                **get_client_notification_context(data),
                'room': 'sample/batch',
            }
        )
        return {
            'type': 'success',
            'body': batch_ids
        }

    async def on_sample_batch_read_request(self, data):
        filters = map_to_snake_case(
            data.get('value', {})
        )
        batches = db.sample_batch_read(**filters)
        return {
            'type': 'success',
            'body': map_to_camel_case(batches)
        }

    async def on_sample_batch_update_request(self, data):
        batches = map_to_snake_case(
            data['value']
        )
        for batch in batches:
            db.sample_batch_update(**batch)
        batch_ids = get_ids(batches)
        await self.notify(
            'sample_batch_event', {'type': 'update', 'ids': batch_ids},
            **{
                **get_client_notification_context(data),
                'room': 'sample/batch',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    async def on_sample_batch_delete_request(self, data):
        batch_ids = data.get['value']
        item_ids = get_ids(
            db.sample_item_read(batchId=batch_ids)
        )
        self.sample_item_delete_request(item_ids)
        db.sample_batch_delete(id=batch_ids)
        await self.notify(
            'sample_batch_event', {'type': 'delete', 'ids': batch_ids},
            **{
                **get_client_notification_context(data),
                'room': 'sample/batch',
            }
        )
        return {
            'type': 'success',
            'body': {
                'batches': batch_ids,
                'items': item_ids
            }
        }

    # === sample items === #

    async def on_sample_item_create_request(self, data):
        items = [{
                'id': gen_id(),
                **item,
            } for item in map_to_snake_case(
                data['value']
            )
        ]
        for item in items:
            db.sample_item_create(**item)
        item_ids = get_ids(items)
        await self.notify(
            'sample_item_event', {'type': 'create', 'ids': item_ids},
            **{
                **get_client_notification_context(data),
                'room': 'sample/item',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    async def on_sample_item_read_request(self, data):
        filters = map_to_snake_case(
            data.get('value', {})
        )
        items = db.sample_item_read(**filters)
        return {
            'type': 'success',
            'body': map_to_camel_case(items)
        }

    async def on_sample_item_update_request(self, data):
        items = map_to_snake_case(
            data['value']
        )
        for item in items:
            db.sample_item_update(**item)
        item_ids = get_ids(items)
        await self.notify(
            'sample_item_event', {'type': 'update', 'ids': item_ids},
            **{
                **get_client_notification_context(data),
                'room': 'sample/item',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    async def on_sample_item_delete_request(self, data):
        item_ids = data['value']
        db.sample_item_delete(id=item_ids)
        await self.notify(
            'sample_item_event', {'type': 'delete', 'ids': item_ids},
            **{
                **get_client_notification_context(data),
                'room': 'sample/item',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    async def on_sample_item_schema_request(self, data):
        # data: {field_name: field_value}
        timeout = data.get('timeout')
        context = get_client_notification_context(data)
        schema = db.sample_item_get_schema()
        # ensure response accepted, when schema not changed
        result = {'schema': schema, 'dummy': time()}
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
        row_update = data['value']
        schema_fields = [column for column, *_ in db.sample_files.schema]
        row_new = {}
        attribs = {}
        for column, value in row_update.items():
            if column in schema_fields:
                row_new[column] = value
            else:
                attribs[column] = value
        row_new['attributes'] = {
            **row_update.get('attributes', {}),
            **attribs,
            }
        # keep existing unmentioned fields intact
        the_rows = db.sample_file_get(id=row_update['id'])
        row_old = {} if not the_rows else the_rows[0]
        db.sample_file_insert(**{**row_old, **row_new})

    async def on_sample_file_list_request(self, data):
        # data: {field_name: field_value}
        timeout = data.get('timeout')
        context = get_client_notification_context(data)
        value = data['value']

        sorted_range_keys = sorted(['column', 'min_value', 'max_value'])
        is_range_request = sorted(value.keys()) == sorted_range_keys
        if is_range_request:
            records = db.sample_file_get_range(**value)
        else:
            records = db.sample_file_get(**value)
        # ensure response generated, when data not changed
        result = {'records': records, 'dummy': time()}
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
        # ensure response accepted, when schema not changed
        result = {'schema': schema, 'dummy': time()}
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
            raise ValueError(
                f"Expected data_type: signal - got {value['data_type']}"
            )
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
                range=value['range']
            )

    # === templates === #

    async def on_template_list_request(self, data):
        # templates = [
        #     {
        #       "name": "template_1",
        #       "type":"sample",
        #       "template":'[{
        #           "label":"fname",
        #           "required":true,
        #           "placeholder":"fname"
        #         },{
        #           "label":"description",
        #           "value":"Predefined description"
        #         },{
        #           "label":"optional attribute"
        #       }]'
        #     },
        #     ...,
        # ]
        template_type = data['value']['type']
        context = get_client_notification_context(data)
        timeout = context.get('timeout')
        records = db.attribute_template_get(type=template_type)
        if timeout:
            return records
        else:
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
            'template': value['template'],
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
        print(
            f"{client.__class__.__name__} : {e.__class__.__name__}({str(e)})"
        )
    except Exception as e:
        print(
            f"{client.__class__.__name__} : {e.__class__.__name__}({str(e)})"
        )
    finally:
        client.shutdown_event.set()
        print('Service stopped.')


if __name__ == '__main__':
    run()
