"""
TOF Service
"""

import os
import asyncio
import numpy as np
from multiprocessing import Queue
from queue import Empty

from karsalib import BaseClientNamespace, BridgeServiceClient, \
                     parse_cmd_args, get_client_notification_args
from karsatof.kgenerator import Acquisition, h5Streamer

acquisition = None
NO_DATA_LOGGING_DEFAULT = True


class TOFServicePublicNamespace(BaseClientNamespace):
    # TOF service public (root) interfaces
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
            await super().subscribe(self.endpoints)
        if self.endpoints_room_data_sources:
            await super().subscribe(self.endpoints_room_data_sources, self.room_data_sources)
        if self.endpoints_room_instrument:
            await super().subscribe(self.endpoints_room_instrument, self.room_instrument)

    async def on_instrument_data_request(self, data):
        await self.emit_client_notification(
                                    'instrument_data',
                                    self.parent.instrument_data,
                                    **{**get_client_notification_args(data),
                                       'room': data['client_room'], }
                                    )


class TOFServicePrivateNamespace(BaseClientNamespace):
    # TOF service private interfaces
    endpoints = [
            # 
            'service_state',
            #
            # TOFControl
            'start_acquisition',
            'stop_acquisition',
            #
            ]
    service_state = dict(
        acquisition_status = 'not_running',
        instrument_status = 'not_ready',
        )

    async def on_start_acquisition(self, data):
        acquisition.start_acquisition()

    async def on_stop_acquisition(self, data):
        acquisition.stop_acquisition()

    
class TOFServiceClient(BridgeServiceClient):
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
                await self.emit_private_notification(
                                            'instrument_status',
                                            'not_ready',
                                            no_data_logging=False
                                            )
                break
            except BadNamespaceError:
                await self.sio.sleep(.1)
                continue
        acquisition = self.acquisition = await self.initialize_kgenerator()
        await self.emit_private_notification(
                                    'instrument_status',
                                    'ready',
                                    no_data_logging=False,
                                    )
        await self.emit_public_notification(
                                    'instrument_data',
                                    self.instrument_data,
                                    room=self.public_ns.room_data_sources,
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
            await self.emit_private_notification(
                                        'acquisition_status',
                                        'running',
                                        )

            filename_base = self.acquisition.filename
            # Prepend with instrument name
            filename = '_'.join([self.private_ns.namespace.strip('/'),
                                 filename_base
                                 ])
            # Replace spaces with underscore
            filename = filename.replace(' ', '_')

            await self.emit_private_notification(
                                        'acquisition_started',
                                        {'filename': filename,
                                         },
                                        )

            await self.emit_private_notification(
                                        'acquisition_coordinates',
                                        {'filename': filename,
                                         'mz': self.acquisition.mz.tobytes(),
                                         't_range': [0, self.acquisition.length]
                                         },
                                        no_data_logging=True
                                        )
            if hasattr(self.acquisition, 'tps_info'):
                await self.emit_private_notification(
                                            'tps_parameter_info',
                                            {'filename': filename,
                                             'tps_info': self.acquisition.tps_info,
                                             },
                                            )
            # Acquisition loop
            self.log("Entering acquisition loop.")
            while True:
                try:
                    spec_data = self.acquisition.spec_queue.get_nowait() # Non-blocking
                    if hasattr(self.acquisition, 'tps_queue'):
                        tps_data = self.acquisition.tps_queue.get() # Blocking, since new data expected
                    else:
                        tps_data = None
                except Empty:
                    # No new data
                    await self.sio.sleep(.1)
                    continue
                
                # Got data
                if spec_data is not None:
                    # Spectrum data
                    await self.emit_private_notification(
                                            'acquired_spectrum',
                                            {**spec_data,
                                             'filename': filename
                                             },
                                            no_data_logging=True
                                            )
                    # Progress
                    await self.emit_private_notification(
                                            'acquisition_progress', 
                                            {'progress': self.acquisition.progress,
                                             },
                                            )
                    if tps_data:
                        # TPS data
                        await self.emit_private_notification(
                                                'acquired_tps_data',
                                                {**tps_data,
                                                 'filename': filename
                                                 },
                                                no_data_logging=True
                                                )
                # Got poison pill
                else:
                    # Finalize acquisition
                    await self.emit_private_notification(
                                            'acquisition_progress', 
                                            {'progress': 100.,
                                             },
                                            )
                    await self.emit_private_notification(
                                            'acquisition_finished', 
                                            {'filename': filename
                                             },
                                            )
                    await self.emit_private_notification(
                                            'acquisition_status',
                                            'not_running',
                                            )
                    self.log("Exiting acquisition loop.")
                    break # Break out of acquisition loop
        # Out of main loop
        # Kill Acquisition
        self.acquisition.shutdown()


def run():
    url, port, namespace = parse_cmd_args()
    # TOFService should always be in private namespace with data producer
    if namespace == '/':
        print("TOFService must be in a private namespace. " +
              "Please restart the service with --ns option."
              )
        return

    client = TOFServiceClient(url,
                              port,
                              ('/', TOFServicePublicNamespace),
                              (namespace, TOFServicePrivateNamespace)
                              )
    # TODO: get instrument_data from corresponding hw_interface
    client.instrument_data = {'name': namespace, 'type': 'Tofwerk_streamer', }
    client.public_ns.room_instrument = namespace
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())


if __name__=='__main__':
    run()
