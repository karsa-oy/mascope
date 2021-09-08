"""
FileStreamer Service
"""

import os
from datetime import datetime

from karsalib.client import (
                        BaseClientNamespace,
                        BaseStreamerClient,
                        run_streamer_service
                        )
from karsalib.util import get_client_notification_args


class FileStreamerPublicNamespace(BaseClientNamespace):
    # raw service public (root) interfaces
    # the public namespace is primarily exposed to the root namespace
    # via a room_instrument = private_namespace_name.
    room_instrument = None
    room_data_sources = 'room_data_sources'

    endpoints = []
    endpoints_room_sid = []
    endpoints_room_data_sources = [
        'instrument_data_request',
        'service_state',
        ]
    endpoints_room_instrument = [
        'instrument_data_request',
        ]

    service_state = dict(
        instrument_data = dict(),
        )

    async def subscribe(self):
        if self.endpoints:
            await super().subscribe(self.endpoints
                                    )
        if self.endpoints_room_sid:
            await super().subscribe(self.endpoints_room_sid,
                                    self.room_sid
                                    )
        if self.endpoints_room_data_sources:
            await super().subscribe(self.endpoints_room_data_sources,
                                    self.room_data_sources
                                    )
        if self.endpoints_room_instrument:
            await super().subscribe(self.endpoints_room_instrument,
                                    self.room_instrument
                                    )

    async def on_instrument_data_request(self, data):
        await self.emit_client_notification(
                                    'instrument_data',
                                    self.parent.instrument_data,
                                    **get_client_notification_args(data)
                                    )


class FileStreamerPrivateNamespace(BaseClientNamespace):
    # raw service private interfaces
    endpoints = [
            'raw_import',
            'raw_import_status',
            'stop_raw_import',
            # 'raw_stream_request',
            'import_raw_table_datetime_range',
            'service_state'
            ]

    service_state = dict(
        instrument_status = 'not_ready',
    )

    async def on_import_raw_table_datetime_range(self, data):
        kwargs = get_client_notification_args(data)
        dt0_json = data['value'].get('dt0', '')
        dt1_json = data['value'].get('dt1', '')
        if dt0_json == '' or dt1_json == '':
            print("Either start or end datetime not given")
            return
        try:
            dt0 = datetime.strptime(dt0_json, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print("dt0 not valid JSON datetime")
            return
        try:
            dt1 = datetime.strptime(dt1_json, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print("dt1 not valid JSON datetime")
            return
        raw_sample_table = await self.parent.data_pool.get_datetime_range(dt0, dt1)
        await self.emit_client_notification('raw_samples',
                                            raw_sample_table,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                            )


    async def on_raw_import(self, data):
        client_room = data['client_room']
        data_1 = {'client_room': client_room, 'files': []}
        for v in data['value']:
            fname = os.path.join(v['path'], v['filename'])
            if not os.path.isfile(fname):
                raise ValueError("File does not exist: %s" %fname)
            data_1['files'].append(fname)
        with self.parent.lock:
            # keep single set of files to import for key=client_room
            self.parent.requests.cache_delete_key(client_room)
            self.parent.requests.cache_put(data_1)


    async def on_raw_import_status(self, data):
        kwargs = get_client_notification_args(data)
        client_room = data['client_room']
        progress_data = []
        for fname, data in self.parent.request_in_progress.get(client_room, {}).items():
            progress_data.append([fname, data['progress']])
        raw_import_data = {
            'progress': progress_data,
            'queue': self.parent.requests.cache.get(client_room, []),
        }
        await self.emit_client_notification('raw_import_data',
                                            raw_import_data,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                           )


    async def on_stop_raw_import(self, data):
        # Without data.value, stop streaming files in progress,
        # otherwise stop files or remove files from import list by filenames
        client_room = data['client_room']
        value = data['value']
        with self.parent.lock:
            if not value:
                # stop all running imports
                for fname, progress_data in self.parent.request_in_progress[client_room].items():
                    self.log(fname)
                    progress_data['streamer'].stop_stream()
            else:
                for v in value:
                    # remove file from import lists if there
                    fname = os.path.join(v['path'], v['filename'])
                    #TODO: possible sync problem - modify CacheQ for get(key) operation
                    requests_data = self.parent.requests.cache.get(client_room, [])
                    for d in requests_data:
                        try:
                            d['files'].remove(fname)
                            self.log(fname)
                        except ValueError:
                            pass
                    # if file is in progress, then stop importing
                    progress_data = self.parent.request_in_progress.get(client_room, {}).get(fname)
                    if progress_data:
                        self.log(fname)
                        progress_data['streamer'].stop_stream()


class FileStreamerServiceClient(BaseStreamerClient):
    def __init__(self, *args, **kwargs):
        # this allows BaseStreamerClient.__init__ to see caller's context,
        # which is needed for dynamic instantiation of a streamer and a data_pool
        super().__init__(*args, **kwargs)

    # @property
    # def instrument_name(self):
    #     return os.path.basename(os.path.normpath(self.data_pool.data_root))

    async def init_service(self):
        await super().init_service()
        assert self.data_pool, 'Missing data_pool argument'
        await self.data_pool.scan_dir(self.data_pool.path)



def run():
    run_streamer_service(FileStreamerServiceClient,
                         FileStreamerPublicNamespace,
                         FileStreamerPrivateNamespace
                        )


if __name__ == '__main__':
    run()