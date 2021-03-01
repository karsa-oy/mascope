"""
TOF Service
"""

import os
import asyncio
import numpy as np
from multiprocessing import Queue
from queue import Empty

from karsalib import BaseClientNamespace, BaseServiceClient, parse_cmd_args
from karsatof.kgenerator import Acquisition


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
        self.log(data['value'])
        if data['value'] == "starting":
            TwStartAcquisition()
        elif data['value'] == "stopping":
            TwStopAcquisition()

    
class TOFServiceClient(BaseServiceClient):
    async def initialize_kacquisition(self, kgenerator=Acquisition):
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
        while True:
            # TODO: TBR python-socketio BadNamespaceError connection bug
            from socketio.exceptions import BadNamespaceError
            try:
                await self.emit_client_notification(
                                            'instrument_status',
                                            'not_ready',
                                            room=INSTRUMENT_NAME,
                                            )
                break
            except BadNamespaceError:
                await self.sio.sleep(.1)
                continue
        self.acquisition = await self.initialize_kacquisition()
        await self.emit_client_notification(
                                    'instrument_status',
                                    'ready',
                                    room=INSTRUMENT_NAME,
                                    )

    async def service_main(self):
        global INSTRUMENT_NAME

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
                                        room=INSTRUMENT_NAME,
                                        cookies=cookies,
                                        )

            filename_base = self.acquisition.filename
            filename = filename_base
            # filename = os.path.join(INSTRUMENT_NAME, filename_base)

            await self.emit_client_notification(
                                        'acquisition_started',
                                        {'filename': filename_base,
                                         },
                                        room=INSTRUMENT_NAME,
                                        cookies=cookies,
                                        )
            await self.emit_client_notification(
                                        'acquisition_coordinates',
                                        {'filename': filename,
                                         'mz': self.acquisition.mz.tobytes(),
                                         't_range': [0, self.acquisition.length]
                                         },
                                        room=INSTRUMENT_NAME,
                                        cookies=cookies,
                                        no_data_logging=True
                                        )
            await self.emit_client_notification(
                                        'tps_parameter_info',
                                        {'filename': filename,
                                         'tps_info': self.acquisition.tps_info,
                                         },
                                        room=INSTRUMENT_NAME,
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
                                            room=INSTRUMENT_NAME,
                                            cookies=cookies,
                                            no_data_logging=True
                                            )
                    # TPS data
                    await self.emit_client_notification(
                                            'acquired_tps_data',
                                            tps_data,
                                            room=INSTRUMENT_NAME,
                                            cookies=cookies,
                                            no_data_logging=True
                                            )
                    # Progress
                    await self.emit_client_notification(
                                            'acquisition_progress', 
                                            {'progress': self.acquisition.progress,
                                             },
                                            room=INSTRUMENT_NAME,
                                            cookies=cookies,
                                            )
                # Got poison pill
                else:
                    # Finalize acquisition
                    await self.emit_client_notification(
                                            'acquisition_progress', 
                                            {'progress': 100.,
                                             },
                                            room=INSTRUMENT_NAME,
                                            cookies=cookies,
                                            )
                    await self.emit_client_notification(
                                            'acquisition_finished', 
                                            {'filename': filename
                                             },
                                            room=INSTRUMENT_NAME,
                                            cookies=cookies,
                                            )
                    await self.emit_client_notification(
                                            'acquisition_status',
                                            'not_running',
                                            room=INSTRUMENT_NAME,
                                            cookies=cookies,
                                            )
                    self.log("Exiting acquisition loop.")
                    break # Break out of acquisition loop
        # Out of main loop
        # Kill Acquisition
        self.acquisition.shutdown()


def run():
    global INSTRUMENT_NAME

    url, port, namespace = parse_cmd_args()

    # TODO: TOFService should always be in private namespace with FileIo
    # if namespace == '/':
    #     print("TOFService must be in a private namespace. " +
    #           "Please restart the service with --ns option."
    #           )
    #     return
    # INSTRUMENT_NAME = namespace.strip('/')
    INSTRUMENT_NAME = "TOF" # :TODO

    client = TOFServiceClient(url, port, (namespace, TOFServiceNamespace))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    INSTRUMENT_NAME = ""
    run()
