"""
TOF Service
"""

import os
import asyncio
import numpy as np
from multiprocessing import Queue
from queue import Empty

from karsalib import BaseClientNamespace, BaseServiceClient, parse_cmd_args
from karsatof.kgenerator import KAcquisition
from karsatof.lib.TofDaq import (
                    TwStartAcquisition,
                    TwStopAcquisition,
                    )

NO_DATA_LOGGING_DEFAULT = True
cookies = None
kacq = None

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

    
class TOFServiceClient(BaseServiceClient):
    async def initialize_kacquisition(self, kgenerator=KAcquisition):
        """
        Initialize KAcquisition instance.
        Returns
        -------
        kacq : KAcquisition
            KAcquisition instance

        TODO: Hard-coded parameters
        """
        while True:
            try:
                kacq = kgenerator(spec_queue=Queue(), tps_queue=Queue())
                kacq.start()
                break
            except Exception as e:
                # Probably TofDaq Recorder not running
                self.log(f'{e}\nRetrying...')
                await self.sio.sleep(2)
                continue
        return kacq


    async def init_service(self):
        global kacq

        while True:
            # TODO: TBR python-socketio BadNamespaceError connection bug
            from socketio.exceptions import BadNamespaceError
            try:
                await self.emit_client_notification('instrument_status',
                                             'not_ready',
                                             no_data_logging=False)
                break
            except BadNamespaceError:
                await self.sio.sleep(.1)
                continue
        kacq = self.kacq = await self.initialize_kacquisition()
        await self.emit_client_notification('instrument_status',
                                    'ready',
                                    no_data_logging=False)


    async def service_main(self):
        global cookies

        while True:    #TODO: shutdown flag?
            try:
                if not self.kacq.acq_active.wait(timeout=.1):
                    await self.sio.sleep(0)
                    continue
            except KeyboardInterrupt:
                break
            await self.emit_client_notification('acquisition_status',
                                        'running',
                                        cookies=cookies,
                                        no_data_logging=False
                                        )

            # Acquisition supplementary information
            filename_h5 = self.kacq.acquired_file
            filename_base_h5 = os.path.basename(filename_h5)
            filename_base = os.path.splitext(filename_base_h5)[0]

            mz = np.array(self.kacq.mz, dtype=np.float32)
            t = np.linspace(0,
                            self.kacq.acq_length,
                            self.kacq.nspectra,
                            dtype=np.float32
                            )
            await self.emit_client_notification('acquisition_started', 
                                        {'filename': filename_base},
                                        cookies=cookies,
                                        no_data_logging=False
                                        )
            await self.emit_client_notification('acquisition_coordinates',
                                        {'filename': filename_base,
                                        'mz': mz.tobytes(),
                                        'time': t.tobytes(),
                                        # 't_range': [ float(t[0]), float(t[-1]) ]
                                        },
                                        cookies=cookies,
                                        no_data_logging=NO_DATA_LOGGING_DEFAULT
                                        )
            tps_info = self.kacq.tps_info
            await self.emit_client_notification('tps_parameter_info',
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
                    spec_data = self.kacq.spec_queue.get_nowait()
                    tps_data = self.kacq.tps_queue.get()
                except Empty:
                    await self.sio.sleep(.1)
                    continue
                
                # Got data
                if spec_data is not None:
                    # Spectrum data
                    speci, ti, spec = spec_data
                    await self.emit_client_notification('acquired_spectrum',
                                                {'filename': filename_base,
                                                'i': speci,
                                                't': ti,
                                                'spec': spec.tobytes(),
                                                },
                                                cookies=cookies,
                                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                                )
                    progress = ((speci+1) / self.kacq.nspectra) * 100. # [%]
                    await self.emit_client_notification('acquisition_progress', 
                                                {'sync': speci,
                                                'progress': progress,
                                                },
                                                cookies=cookies,
                                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                                )
                    # TPS data
                    speci, tps_data = tps_data
                    await self.emit_client_notification(
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
                    await self.emit_client_notification('acquisition_progress', 
                                                {'filename': filename_base,
                                                 'progress': progress,
                                                },
                                                cookies=cookies,
                                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                                )
                    await self.emit_client_notification('acquisition_finished', 
                                                {'filename': filename_base},
                                                cookies=cookies,
                                                no_data_logging=False
                                                )
                    await self.emit_client_notification('acquisition_status',
                                                'not_running',
                                                cookies=cookies,
                                                no_data_logging=False
                                                )
                    break
        # Kill KAcquisition
        self.kacq.shutdown()


def run():
    client = TOFServiceClient(*parse_cmd_args(), TOFServiceNamespace)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
