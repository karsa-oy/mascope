"""
TOF Service
"""


from karsalib.client import (
                        BaseClientNamespace,
                        TOFStreamerClient,
                        run_streamer_service
                        )
from karsalib.util import get_client_notification_context


NO_DATA_LOGGING_DEFAULT = True


class TOFServicePublicNamespace(BaseClientNamespace):
    # TOF service public (root) interfaces
    # the public namespace is primarily exposed to the root namespace
    # as room_instrument = private_namespace_name (set by BaseStreamClient init)

    service_state = dict(
        instrument_data = {'value': dict(), 'room': 'room_data_sources'},
        )

    async def on_connect(self):
        await self.enter_room(self.room_instrument)
        await super().on_connect()

    async def on_instrument_data_request(self, data):
        await self.emit_client_notification(
                                    'instrument_data',
                                    self.parent.instrument_data,
                                    **{**get_client_notification_context(data),
                                       'room': data['client_room'], }
                                    )


class TOFServicePrivateNamespace(BaseClientNamespace):
    # TOF service private interfaces

    service_state = dict(
        acquisition_status = {'value': 'not_running', 'room': None},
        instrument_status = {'value': 'not_ready', 'room': None},
        )

    async def on_tofdaq_log_entry(self, data):
        value = data['value']
        text = value['text']
        timestamp = value['timestamp']
        self.parent.streamer.add_log_entry(text, timestamp)


    async def on_start_acquisition(self, data):
        self.parent.streamer.start_acquisition()

    async def on_stop_acquisition(self, data):
        self.parent.streamer.stop_acquisition()

    
class TOFServiceClient(TOFStreamerClient):
    # TofDaq Recorder must be running.

    def __init__(self, streamer_type, data_pool,
                 url, port, public_namespace_data, private_namespace_data):
        super().__init__(streamer_type or 'TofDaq', data_pool,
                         url, port, public_namespace_data, private_namespace_data)
        self.acknowledge_acquisition = False    # do not sync acq.speed with FileIO capacity

    async def init_service(self):
        await super().init_service()
        assert self.data_pool == None, 'TofDaq service does not use data_pool argument'


def run():
    run_streamer_service(TOFServiceClient,
                         TOFServicePublicNamespace,
                         TOFServicePrivateNamespace
                        )


if __name__ == '__main__':
    run()
