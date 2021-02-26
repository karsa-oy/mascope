"""
TWh5Streamer Service
"""

import asyncio
import os
import numpy as np

from multiprocessing import Queue
from queue import Empty
from datetime import datetime

from karsalib import BaseClientNamespace, parse_cmd_args
from tof_service.TOFService import TOFServiceClient
from karsatof.kgenerator import KStreamer
from karsatof.kdatapool import H5Pool


kacq = None

# TODO: make platform-agnostic (move to settings file)
drive_letter = 'Z:\\'
h5_dir = os.path.join('Data', 'raw_KLTOF2')
h5_path = os.path.join(drive_letter, h5_dir)
h5_pool = H5Pool(h5_path)


class TWh5StreamerNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for
        connecting to Router """

    endpoints = ['h5_to_import',
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

        dt0_json = data.get('dt0', '')
        dt1_json = data.get('dt1', '')
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
                                            no_data_logging=True
                                            )

    async def on_h5_to_import(self, data):
        print("on_h5_to_import: %s" %str(data))
        for h5 in data:
            full_file_path = os.path.join( h5.get('path'), h5.get('filename') )
            await self.on_h5_stream_request( {'filename': full_file_path} )

    async def on_h5_stream_request(self, data):
        global kacq

        filename = data.get('filename', None)
        if filename is None:
            raise ValueError("Received data_request without filename")

        if not os.path.exists(filename):
            raise ValueError("Received filename does not exist")

        print("Putting to file_queue: %s" %filename)
        kacq.file_queue.put(filename)


class TWh5StreamerServiceClient(TOFServiceClient):
    async def  init_service(self):
        global kacq

        while True:
            # TODO: TBR python-socketio BadNamespaceError connection bug
            from socketio.exceptions import BadNamespaceError
            try:
                await self.emit_client_notification('h5_streamer_status', 
                                             'not_ready',
                                             no_data_logging=False)
                break
            except BadNamespaceError:
                await self.sio.sleep(.1)
                continue
        kacq = self.kacq = await self.initialize_kacquisition(KStreamer)
        await h5_pool.scan_dir(h5_path)
        await self.emit_client_notification('h5_streamer_status',
                                    'ready',
                                    no_data_logging=False)


def run():
    client = TWh5StreamerServiceClient(*parse_cmd_args(), TWh5StreamerNamespace)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        kacq.shutdown()


if __name__=='__main__':
    run()
