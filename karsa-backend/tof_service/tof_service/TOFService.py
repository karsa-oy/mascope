"""TOF Service
"""

import os
import sys
import getopt
import asyncio
import socketio
import numpy as np

from multiprocessing import Queue
from queue import Empty

from helpers import BaseClientNamespace

from karsatof.kgenerator import KAcquisition
from karsatof.lib.TofDaq import (
                    TwStartAcquisition,
                    TwStopAcquisition,
                    )

NO_DATA_LOGGING_DEFAULT = True
root_ns = None
cookies = None

class TOFServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for
        connecting to Router """

    rooms = ['acquisition_status',
             'data_write_path',
             'service_state'
             ]

    service_state = dict(
        acquisition_status = 'not_running',
        instrument_status = 'not_ready',
        )

    async def on_acquisition_status(self, data):
        global cookies
        cookies = data['cookies']
        self.log(data['value'])
        if data['value'] == "starting":
            TwStartAcquisition()
        elif data['value'] == "stopping":
            TwStopAcquisition()

    async def on_data_write_path(self, new_path):
        """Change TofDaq Recorder write path

        Parameters
        ----------
        new_path : str or bytes
            New write path
        """

        global kacq
        self.log(new_path)
        try:
            if type(new_path) == str:
                new_path = new_path.encode()
            kacq.set_save_path(new_path)
        except Exception as e:
            self.log(f'Failed: {e}')
    

async def run_service(url, port):
    addr = f'{url}:{port}'
    if not addr.startswith('http'):
        addr = 'http://' + addr
    sio, kacq = await init_service(addr)
    await main(sio, kacq)


async def init_service(addr):
    sio = socketio.AsyncClient()
    sio.register_namespace(TOFServiceNamespace('/'))

    while True:
        try:
            print('Connecting to Router...')
            await sio.connect(addr, namespaces=['/',])
            print("Connected!")
            break
        except socketio.exceptions.ConnectionRefusedError as e:
            print("Failed.", e)
            await sio.sleep(2)

    global root_ns
    root_ns = sio.namespace_handlers['/']

    while True:
        # TODO: TBR workaround for python-socketio connection bug
        try:
            await emit_client_notification('instrument_status',
                                           'not_ready',
                                           no_data_logging=False
                                           )
            break
        except socketio.exceptions.BadNamespaceError:
            await sio.sleep(.1)
            continue

    kacq = await initialize_kacquisition()
    await emit_client_notification('instrument_status',
                                   'ready',
                                   no_data_logging=False
                                   )
    return sio, kacq


async def emit_client_notification(name, value, **kwarg):
    global root_ns
    await root_ns.emit_client_notification(name,
                                           value,
                                           **kwarg
                                           )


async def initialize_kacquisition(kgenerator=KAcquisition):
    """Initialize KAcquisition instance
    
    Returns
    -------
    kacq : KAcquisition
        KAcquisition instance

    TODO: Hard-coded parameters
    """

    while True:
        try:
            # Initialize KAcquisition
            kacq = kgenerator(
                        spec_queue=Queue(),
                        tps_queue=Queue()
                        )
            kacq.start()
            break
        except Exception as e:
            # Probably TofDaq Recorder not running
            print(e)
            await asyncio.sleep(2)
            print("Retrying...")
    return kacq


async def main(sio, kacq):
    """
    Main event loop of the service
    """
    
    global root_ns
    root_ns = sio.namespace_handlers['/']

    condition = True #TODO: Implement shutdown flag?

    while condition:
        # Wait for acquisition
        try:
            if not kacq.acq_active.wait(timeout=.1):
                await sio.sleep(0)
                continue
        except KeyboardInterrupt:
            break
        # Acquisition started
        await emit_client_notification('acquisition_status',
                                       'running',
                                       cookies=cookies,
                                       no_data_logging=False
                                       )

        # Acquisition supplementary information
        filename_h5 = kacq.acquired_file
        filename_base_h5 = os.path.basename(filename_h5)
        filename_base = os.path.splitext(filename_base_h5)[0]

        mz = np.array(kacq.mz, dtype=np.float32)
        t = np.linspace(0,
                        kacq.acq_length,
                        kacq.nspectra,
                        dtype=np.float32
                        )

        await emit_client_notification('acquisition_started', 
                                       {'filename': filename_base},
                                       cookies=cookies,
                                       no_data_logging=False
                                       )
        await emit_client_notification('acquisition_coordinates',
                                       {'filename': filename_base,
                                        'mz': mz.tobytes(),
                                        'time': t.tobytes(),
                                        # 't_range': [ float(t[0]), float(t[-1]) ]
                                        },
                                       cookies=cookies,
                                       no_data_logging=NO_DATA_LOGGING_DEFAULT
                                       )
        # TPS parameter info
        tps_info = kacq.tps_info
        await emit_client_notification('tps_parameter_info',
                                       {'filename': filename_base,
                                        'tps_info': tps_info,
                                        # 'time': t.tobytes()
                                        },
                                       cookies=cookies,
                                       no_data_logging=NO_DATA_LOGGING_DEFAULT
                                       )

        # Acquisition loop
        while True:
            try:
                spec_data = kacq.spec_queue.get_nowait()
                tps_data = kacq.tps_queue.get()
            except Empty:
                await sio.sleep(.1)
                continue
            
            # Got data
            if spec_data is not None:
                # Spectrum data
                speci, ti, spec = spec_data
                await emit_client_notification('acquired_spectrum',
                                               {'filename': filename_base,
                                                'i': speci,
                                                't': ti,
                                                'spec': spec.tobytes(),
                                                },
                                               cookies=cookies,
                                               no_data_logging=NO_DATA_LOGGING_DEFAULT
                                               )
                progress = ((speci+1) / kacq.nspectra) * 100. # [%]
                await emit_client_notification('acquisition_progress', 
                                               {'sync': speci,
                                                'progress': progress,
                                                },
                                               cookies=cookies,
                                               no_data_logging=NO_DATA_LOGGING_DEFAULT
                                               )
                # TPS data
                speci, tps_data = tps_data
                await emit_client_notification(
                                        'acquired_tps_data',
                                        {'filename': filename_base,
                                         'i': speci,
                                         't': ti,
                                         'tps_data': tps_data.tobytes(),
                                         },
                                        cookies=cookies,
                                        no_data_logging=NO_DATA_LOGGING_DEFAULT
                                        )
            # Got poison pill
            else:
                # Finalize acquisition
                await emit_client_notification('acquisition_progress', 
                                               {'filename': filename_base,
                                                'progress': progress,
                                                },
                                               cookies=cookies,
                                               no_data_logging=NO_DATA_LOGGING_DEFAULT
                                               )
                await emit_client_notification('acquisition_finished', 
                                               {'filename': filename_base},
                                               cookies=cookies,
                                               no_data_logging=False
                                               )
                await emit_client_notification('acquisition_status',
                                               'not_running',
                                               cookies=cookies,
                                               no_data_logging=False
                                               )
                break
    # Kill KAcquisition
    kacq.shutdown()


def parse_cmd_args():
    """Parse command line arguments
    Allowed command line arguments
    ------------------------------
    --url : string
        IP address (localhost)
    --port : int
        Server port (5010)
    """
    url = 'localhost'
    port = 5010
    opts, _ = getopt.getopt(
                    sys.argv[1:],
                    'o:v',
                    ['url=', 'port=', ]
                    )
    for opt, arg in opts:
        if opt=='--url':
            url = arg
        if opt=='--port':
            try:
                port = int(arg)
            except:
                print('Invalid command line argument: %s=%s' %(opt, arg))
    return url, port


def run():
    url, port = parse_cmd_args()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_service(url, port))


if __name__=='__main__':
    run()
