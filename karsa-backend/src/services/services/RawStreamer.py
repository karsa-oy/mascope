"""
RawStreamer Service
"""

import os
from datetime import datetime

from karsalib.client import (
                        BaseClientNamespace,
                        BaseStreamerClient,
                        run_streamer_service
                        )
from karsalib.util import get_client_notification_args


class RawStreamerPublicNamespace(BaseClientNamespace):
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


class RawStreamerPrivateNamespace(BaseClientNamespace):
    # raw service private interfaces
    endpoints = [
            'raw_import',
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

        raw_sample_table = await self.parent.raw_pool.get_datetime_range(dt0, dt1)

        await self.emit_client_notification('raw_samples',
                                            raw_sample_table,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                            )

    async def on_raw_import(self, data):
        for raw_file in data['value']:
            full_file_path = os.path.join( raw_file.get('path'), raw_file.get('filename') )
            self.parent.streamer.start_stream(full_file_path)

    async def on_stop_raw_import(self, data):
        # TODO: do we need to remove only specific files from the queue?
        # for raw_file in data['value']:
        #     full_file_path = os.path.join( raw_file.get('path'), raw_file.get('filename') )
        #     self.parent.streamer.stop_stream(full_file_path)
        self.parent.streamer.stop_stream()


class RawStreamerServiceClient(BaseStreamerClient):
    def __init__(self, *args, **kwargs):
        # this allows BaseStreamerClient.__init__ to see caller's context,
        # which is needed for dynamic instantiation of a streamer and a raw_pool
        super().__init__(*args, **kwargs)

    # @property
    # def instrument_name(self):
    #     return os.path.basename(os.path.normpath(self.raw_pool.data_root))

    async def init_service(self):
        await super().init_service()
        assert self.raw_pool, 'Missing raw_pool argument'
        await self.raw_pool.scan_dir(self.raw_pool_path)



def run():
    run_streamer_service(RawStreamerServiceClient,
                         RawStreamerPublicNamespace,
                         RawStreamerPrivateNamespace
                        )


if __name__ == '__main__':
    run()