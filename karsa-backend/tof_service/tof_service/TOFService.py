"""
TOF Service
"""


from karsalib import BaseClientNamespace, get_client_notification_args, \
                     BaseStreamerClient, run_streamer_service
from karsatof.kgenerator import Acquisition


NO_DATA_LOGGING_DEFAULT = True


class TOFServicePublicNamespace(BaseClientNamespace):
    # TOF service public (root) interfaces
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
        self.parent.streamer.start_acquisition()

    async def on_stop_acquisition(self, data):
        self.parent.streamer.stop_acquisition()

    
class TOFServiceClient(BaseStreamerClient):
    # TofDaq Recorder must be running.
    pass


def run():
    run_streamer_service('Tofwerk_streamer',
                         TOFServiceClient,
                         Acquisition,
                         TOFServicePublicNamespace,
                         TOFServicePrivateNamespace
                        )


if __name__ == '__main__':
    run()
