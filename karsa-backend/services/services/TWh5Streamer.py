"""TOF Service
"""

import asyncio
import socketio
import os
import numpy as np

from multiprocessing import Queue
from queue import Empty
from datetime import datetime

from helpers import BaseClientNamespace

from karsatof.kgenerator import KStreamer
from karsatof.kdatapool import H5Pool

from tof_service.TOFService import initialize_kacquisition, main


sio = None
root_ns = None
kacq = None
shutdown_event = None

drive_letter = 'Z:\\'
h5_dir = os.path.join('Data', 'raw_KLTOF2')
h5_path = os.path.join(drive_letter, h5_dir)
h5_pool = H5Pool(h5_path)


class TWh5StreamerNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for
        connecting to Router """

    rooms = ['h5_to_import',
             'h5_stream_request',
             'import_h5_table_datetime_range',
             'service_state'
             ]

    service_state = dict(
        h5_streamer_status = dict(value='not_ready')
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



async def run_service():
    global kacq
    global sio
    sio, kacq = await init_service('http://localhost:5010')
    await main(sio, kacq)


async def init_service(url):
    global root_ns
    global h5_pool

    sio = socketio.AsyncClient()
    sio.register_namespace(TWh5StreamerNamespace('/'))

    while True:
        try:
            print('Connecting to Router...')
            await sio.connect(url, namespaces=['/',])
            await sio.sleep(.1)
            print("Connected!")
            break
        except:
            print('Failed')
    root_ns = sio.namespace_handlers['/']

    await emit_client_notification('h5_streamer_status',
                                   dict(value='not_ready')
                                   )
    # Initialize KStreamer
    kacq = await initialize_kacquisition(KStreamer)
    # Scan given directory for h5 files
    await h5_pool.scan_dir(h5_path)
    # Ready
    await emit_client_notification('h5_streamer_status',
                                   dict(value='ready')
                                   )
    return sio, kacq


async def emit_client_notification(name, value, **kwarg):
    global root_ns
    await root_ns.emit_client_notification(name,
                                           value,
                                           **kwarg
                                           )

def run():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_service())
    except KeyboardInterrupt:
        kacq.shutdown()

if __name__=='__main__':
    run()