"""
TWh5Streamer Service
"""

import asyncio
import os
import numpy as np

from multiprocessing import Queue
from queue import Empty
from datetime import datetime

from karsalib import (
                BaseClientNamespace,
                parse_cmd_args,
                get_client_notification_args
                )
from tof_service.TOFService import TOFServiceClient
from karsatof.kgenerator import h5Streamer
from karsatof.kdatapool import H5Pool


h5streamer = None


# TODO: make platform-agnostic (move to settings file)
drive_letter = 'Z:\\'
h5_dir = os.path.join('Data', 'raw_KLTOF2')


h5_path = os.path.join(drive_letter, h5_dir)
h5_pool = H5Pool(h5_path)


class TWh5StreamerPublicNamespace(BaseClientNamespace):
    # h5 service public (root) interfaces
    parent = None
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
        h5_streamer_status = 'not_ready',
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
            self.stream_h5(full_file_path)

    def stream_h5(self, h5_filepath):
        global h5streamer
        h5streamer.start_stream(h5_filepath)


class TWh5StreamerServiceClient(TOFServiceClient):
    async def init_service(self):
        global h5streamer

        while True:
            # TODO: TBR python-socketio BadNamespaceError connection bug
            from socketio.exceptions import BadNamespaceError
            try:
                await self.emit_private_notification('h5_streamer_status', 
                                                     'not_ready',
                                                     no_data_logging=False
                                                     )
                break
            except BadNamespaceError:
                await self.sio.sleep(.1)
                continue
        h5streamer = self.acquisition = await self.initialize_kgenerator(
                                                                    h5Streamer
                                                                    )
        await h5_pool.scan_dir(h5_path)
        await self.emit_private_notification('h5_streamer_status',
                                             'ready',
                                             no_data_logging=False
                                             )
        await self.emit_public_notification(
                                'instrument_data',
                                self.instrument_data,
                                room=self.public_ns.room_data_sources,
                                no_data_logging=False
                                )


def run():
    global h5streamer

    url, port, namespace = parse_cmd_args()
    # h5 streamer should always be in private namespace with data producer
    if namespace == '/':
        print("TWh5StreamerService must be in a private namespace. " +
              "Please restart the service with --ns option."
              )
        return

    client = TWh5StreamerServiceClient(url,
                                       port,
                                       ('/', TWh5StreamerPublicNamespace),
                                       (namespace, TWh5StreamerPrivateNamespace)
                                       )
    client.instrument_data = {'name': namespace,
                              }
    client.public_ns.room_instrument = namespace

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        h5streamer.shutdown()


if __name__=='__main__':
    run()
