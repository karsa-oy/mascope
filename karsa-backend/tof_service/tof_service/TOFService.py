"""
TOF Service
"""


from karsalib import BaseClientNamespace, get_client_notification_args, \
                     BaseStreamerClient, run_streamer_service
from karsatof.kgenerator import TofDaqStreamer


NO_DATA_LOGGING_DEFAULT = True


class TOFServicePublicNamespace(BaseClientNamespace):
    # TOF service public (root) interfaces
    # the public namespace is primarily exposed to the root namespace
    # via a room_instrument = private_namespace_name (set by BaseStreamClient init)
    room_instrument = None
    room_data_sources = 'room_data_sources'
    endpoints = []
    endpoints_room_sid = []
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
        if self.endpoints_room_sid:
            await super().subscribe(self.endpoints_room_sid, self.room_sid)
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
            'instrument_log_entry',
            'start_acquisition',
            'stop_acquisition',
            #
            ]
    service_state = dict(
        acquisition_status = 'not_running',
        instrument_status = 'not_ready',
        )

    async def on_instrument_log_entry(self, data):
        # TODO: Write to file
        self.log(data['value'])

    async def on_start_acquisition(self, data):
        self.parent.streamer.start_acquisition()

    async def on_stop_acquisition(self, data):
        self.parent.streamer.stop_acquisition()

    
class TOFServiceClient(BaseStreamerClient):
    # TofDaq Recorder must be running.

    def __init__(self, streamer_type, raw_pool,
                 url, port, public_namespace_data, private_namespace_data):
        # this allows BaseStreamerClient.__init__ to see caller's context,
        # which is needed for dynamic instantiation of a streamer and a raw_pool
        super().__init__(streamer_type or 'TofDaq', raw_pool,
                         url, port, public_namespace_data, private_namespace_data)

    async def init_service(self):
        await super().init_service()
        assert self.raw_pool == None, 'TofDaq service does not use raw_pool argument'


def run():
    run_streamer_service(TOFServiceClient,
                         TOFServicePublicNamespace,
                         TOFServicePrivateNamespace
                        )


if __name__ == '__main__':
    run()
