import asyncio

from backend.service.lib.client import BaseClientNamespace, BaseServiceClient

from backend.lib.util import get_client_notification_context, parse_cmd_args
from backend.lib.struct import AttrDict, LRUDict
from backend.lib.file import (
    zarr_sdk,
    append_instrument_log,
    read_instrument_log,
)

from backend.server import sio


DATA_VERSION_NUMBER = '0.01'

client = None

# Cache for data arrays
cache = LRUDict(10)


class FileIoNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to MainService """

    service_state = dict()

    # ========== TOFControl requests ==========

    async def on_instrument_log_entry(self, data):
        value = data['value']
        entry = value
        append_instrument_log(self.namespace.strip('/'), entry)

    async def on_instrument_log_request(self, data):
        client_room = data['cookies']['src_sid'][0]
        log = read_instrument_log(self.namespace.strip('/'))
        await self.emit_client_notification('instrument_log',
                                            log,
                                            room=client_room
                                            )
    # -----------------------------------------

    # ========== TOFService requests ==========
    async def on_acquisition_coordinates(self, data):
        """Initialize acquisition cache with received coordinates

        Parameters
        ----------
        data : dict
            keys: 'mz' and 'time'
        """
        global cache
        filename = data['value']['filename']
        self.log(filename)
        kwargs = get_client_notification_context(data)
        try:
            cache_item = zarr_sdk.init_signal_dataset(data)
        except FileExistsError:
            self.log(f"FileExistsError: {filename} acquisition cancelled")
            await self.emit_client_notification('stop_raw_import', {
                }, **kwargs)
            return {}
        cache_item = AttrDict(cache_item)
        cache[filename] = cache_item
        return data['callback_data']

    async def on_acquired_spectrum(self, data):
        """Receive new spectrum, add to cache

        Parameters
        ----------
        data : dict
            keys: 'filename', 'i', 't', 'spec', 'period', ('mz')
        """
        global cache
        filename = data['value']['filename']
        cache_item = cache.get(filename)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        zarr_sdk.update_signal_dataset(data, cache_item)
        if cache_item['signal'].delayed_write is None:
            # updates to signal mfzarrs are committed - notify
            await sio.emit('dataset_updated', {
                'data_type': 'signal',
                **cache_item['props']
            }, namespace='/api')
        return data['callback_data']

    async def on_acquired_tps_data(self, data):
        global cache
        filename = data['value']['filename']
        cache_item = cache.get(filename)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        zarr_sdk.update_tps_dataset(data, cache_item)

    async def on_acquisition_finished(self, data):
        global cache
        filename = data['value']['filename']
        cache_item = cache.get(filename)
        self.log(filename)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        try:
            zarr_sdk.finalize_signal_dataset(data, cache_item)
        except Exception as error:
            print(error)
            pass    # let client services finalize the request anyway
        await sio.emit('dataset_updated', {
            'data_type': 'signal',
            **cache_item['props']
        }, namespace='/api')

    async def on_tps_parameter_info(self, data):
        global cache
        filename = data['value']['filename']
        self.log(filename)
        cache_item = cache.get(filename)
        if not cache_item:
            self.log(f"Warning: {filename} was skipped")
            return
        zarr_sdk.init_tps_dataset(data, cache_item)


class FileIoClient(BaseServiceClient):
    async def init_service(self):
        return

    async def service_main(self):
        while True:
            try:
                await self.sio.sleep(.5)
            except KeyboardInterrupt:
                break
            # End of main loop
        await self.sio.disconnect()


def run():
    args = parse_cmd_args()
    # FileIo should always be in private namespace with data producer
    if args['ns'] == '/':
        print("file_io must be in a private namespace. " +
              "Please restart the service with --ns option."
              )
        return

    client = FileIoClient(args['url'],
                          args['port'],
                          (args['ns'], FileIoNamespace)
                          )

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        client.shutdown_event.set()
        print('Service stopped.')


if __name__ == '__main__':
    run()
