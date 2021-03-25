"""
TWh5Streamer Service
"""

import os

from karsalib import BaseClientNamespace, get_client_notification_args, \
                     BaseStreamerClient, run_streamer_service
from karsatof.kgenerator import h5Streamer
from karsatof.kdatapool import H5Pool


# TODO: make platform-agnostic (move to settings file)
drive_letter = 'Z:\\'
h5_dir = os.path.join('Data', 'raw_KLTOF2')


h5_path = os.path.join(drive_letter, h5_dir)
h5_pool = H5Pool(h5_path)


class TWh5StreamerPublicNamespace(BaseClientNamespace):
    # h5 service public (root) interfaces
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

class TWh5StreamerPrivateNamespace(BaseClientNamespace):
    # h5 service private interfaces
    endpoints = [
            'h5_to_import',
            'h5_stream_request',
            'import_h5_table_datetime_range',
            'service_state'
            ]

    service_state = dict(
        instrument_status = 'not_ready',
    )

    async def on_import_h5_table_datetime_range(self, data):
        global h5_path
        global h5_pool

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

        h5_sample_table = await h5_pool.get_datetime_range(dt0, dt1)

        await self.emit_client_notification('h5_samples',
                                            h5_sample_table,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                            )

    async def on_h5_to_import(self, data):
        for h5 in data['value']:
            full_file_path = os.path.join( h5.get('path'), h5.get('filename') )
            self.parent.streamer.start_stream(full_file_path)


class TWh5StreamerServiceClient(BaseStreamerClient):
    async def init_service(self):
        global h5_pool
        await h5_pool.scan_dir(h5_path)
        await super().init_service()



def run():
    run_streamer_service('h5_streamer',
                         TWh5StreamerServiceClient,
                         h5Streamer,
                         TWh5StreamerPublicNamespace,
                         TWh5StreamerPrivateNamespace
                        )


if __name__ == '__main__':
    run()