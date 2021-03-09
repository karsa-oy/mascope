"""
TOF Service
"""

import os
import asyncio
import numpy as np
from multiprocessing import Queue
from queue import Empty

from karsalib import BaseClientNamespace, BaseServiceClient, parse_cmd_args
from karsatof.kgenerator import Acquisition, h5Streamer

acquisition = None
NO_DATA_LOGGING_DEFAULT = True

class TOFServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for
        connecting to Router """

    endpoints = [
            'acquisition_status',
            'data_write_path',
            'service_state'
            ]

    service_state = dict(
        acquisition_status = 'not_running',
        instrument_status = 'not_ready',
        )

    async def on_acquisition_status(self, data):
        global acquisition
        self.log(data['value'])
        if data['value'] == "starting":
            acquisition.start_acquisition()
        elif data['value'] == "stopping":
            acquisition.stop_acquisition()

    
class TOFServiceClient(BaseServiceClient):
    async def initialize_kgenerator(self, kgenerator=Acquisition):
        """
        Initialize KAcquisition instance.

        TofDaq Recorder must be running.

        Returns
        -------
        kgenerator
            Acquisition or Streamer class instance

        """
        while True:
            try:
                acquisition = kgenerator()
                acquisition.start()
                break
            except Exception as e:
                # Probably TofDaq Recorder not running
                self.log(f'{e}\nRetrying...')
                await self.sio.sleep(2)
                continue
        return acquisition


    async def init_service(self):
        global acquisition
        
        while True:
            # TODO: TBR python-socketio BadNamespaceError connection bug
            from socketio.exceptions import BadNamespaceError
            try:
                await self.emit_client_notification(
                                            'instrument_status',
                                            'not_ready',
                                            no_data_logging=False
                                            )
                break
            except BadNamespaceError:
                await self.sio.sleep(.1)
                continue
        acquisition = self.acquisition = await self.initialize_kgenerator()
        await self.emit_client_notification(
                                    'instrument_status',
                                    'ready',
                                    no_data_logging=False
                                    )

    async def service_main(self):
        # Main loop
        while True:
            # Catch Ctrl+C
            try:
                # Check for active acquisition
                if not self.acquisition.active.wait(timeout=.1):
                    await self.sio.sleep(0)
                    # Not yet
                    continue
            except KeyboardInterrupt:
                # Exit
                break

            # Initialize acquisition
            self.log("Initializing acquisition.")
            cookies = dict(src_sid=[])  # make tofservice originator of the requests
            await self.emit_client_notification(
                                        'acquisition_status',
                                        'running',
                                        cookies=cookies,
                                        )

            filename_base = self.acquisition.filename
            filename = filename_base

            await self.emit_client_notification(
                                        'acquisition_started',
                                        {'filename': filename,
                                         },
                                        cookies=cookies,
                                        )
            await self.emit_client_notification(
                                        'acquisition_coordinates',
                                        {'filename': filename,
                                         'mz': self.acquisition.mz.tobytes(),
                                         't_range': [0, self.acquisition.length]
                                         },
                                        cookies=cookies,
                                        no_data_logging=True
                                        )
            await self.emit_client_notification(
                                        'tps_parameter_info',
                                        {'filename': filename,
                                         'tps_info': self.acquisition.tps_info,
                                         },
                                        cookies=cookies,
                                        )
            # Acquisition loop
            self.log("Entering acquisition loop.")
            while True:
                try:
                    spec_data = self.acquisition.spec_queue.get_nowait() # Non-blocking
                    tps_data = self.acquisition.tps_queue.get() # Blocking, since new data expected
                except Empty:
                    # No new data
                    await self.sio.sleep(.1)
                    continue
                
                # Got data
                if spec_data is not None:
                    # Spectrum data
                    await self.emit_client_notification(
                                            'acquired_spectrum',
                                            spec_data,
                                            cookies=cookies,
                                            no_data_logging=True
                                            )
                    # TPS data
                    await self.emit_client_notification(
                                            'acquired_tps_data',
                                            tps_data,
                                            cookies=cookies,
                                            no_data_logging=True
                                            )
                    # Progress
                    await self.emit_client_notification(
                                            'acquisition_progress', 
                                            {'progress': self.acquisition.progress,
                                             },
                                            cookies=cookies,
                                            )
                # Got poison pill
                else:
                    # Finalize acquisition
                    await self.emit_client_notification(
                                            'acquisition_progress', 
                                            {'progress': 100.,
                                             },
                                            cookies=cookies,
                                            )
                    await self.emit_client_notification(
                                            'acquisition_finished', 
                                            {'filename': filename
                                             },
                                            cookies=cookies,
                                            )
                    await self.emit_client_notification(
                                            'acquisition_status',
                                            'not_running',
                                            cookies=cookies,
                                            )
                    self.log("Exiting acquisition loop.")
                    break # Break out of acquisition loop
        # Out of main loop
        # Kill Acquisition
        self.acquisition.shutdown()


def run():
    url, port, namespace = parse_cmd_args()

    # TODO: TOFService should always be in private namespace with FileIo
    # if namespace == '/':
    #     print("TOFService must be in a private namespace. " +
    #           "Please restart the service with --ns option."
    #           )
    #     return

    client = TOFServiceClient(url, port, (namespace, TOFServiceNamespace))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
