"""
RawStreamer Service
"""

import os

from karsalib import BaseClientNamespace, get_client_notification_args, \
                     BaseStreamerClient, run_streamer_service
from karsatof.kgenerator import RawStreamer
from karsatof.kdatapool import RawPool


# TODO: make platform-agnostic (move to settings file)
drive_letter = 'Z:\\'
raw_dir = os.path.join(drive_letter,
                       'Data',
                       'Orbitrap Data and Documents',
                       'Orbitrap Data 2020'
                       )

raw_path = os.path.join(drive_letter, raw_dir)
raw_pool = RawPool(raw_path)


class RawStreamerPublicNamespace(BaseClientNamespace):
    # raw service public (root) interfaces
    # the public namespace is primarily exposed to the root namespace
    # via a room_instrument = private_namespace_name.
    room_instrument = None
    room_data_sources = 'room_data_sources'

    endpoints = []

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
            'raw_to_import',
            'raw_stream_request',
            'import_raw_table_datetime_range',
            'service_state'
            ]

    service_state = dict(
        instrument_status = 'not_ready',
    )

    async def on_import_raw_table_datetime_range(self, data):
        global raw_path
        global raw_pool

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

        raw_sample_table = await raw_pool.get_datetime_range(dt0, dt1)

        await self.emit_client_notification('raw_samples',
                                            raw_sample_table,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                            )

    async def on_raw_to_import(self, data):
        for raw_file in data['value']:
            full_file_path = os.path.join( raw_file.get('path'), raw_file.get('filename') )
            self.parent.streamer.start_stream(full_file_path)
        


class RawStreamerServiceClient(BaseStreamerClient):
    async def init_service(self):
        global raw_pool
        await raw_pool.scan_dir(raw_path)
        await super().init_service()



def run():
    run_streamer_service('raw_streamer',
                         RawStreamerServiceClient,
                         RawStreamer,
                         RawStreamerPublicNamespace,
                         RawStreamerPrivateNamespace
                        )


if __name__ == '__main__':
    run()