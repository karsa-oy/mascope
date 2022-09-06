import asyncio
import inspect
import os
import socketio

from backend.api.match import match_item_compute
from backend.api.sample import sample_file_create
from backend.lib.file import zarr_sdk
from backend.lib.hardware.tofwerk.generator import H5Streamer
from backend.lib.hardware.orbitrap.generator import RawStreamer
from backend.lib.struct import AttrDict, LRUDict
from backend.lib.util import parse_cmd_args, timestamp_from_filename

from datetime import timedelta
from dotenv import load_dotenv
from multiprocessing import Event, Queue, Lock
from queue import Empty
from threading import Thread
from time import sleep
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, mask):
            if not isinstance(mask, list):
                mask = [mask, ]
            super().__init__(patterns=mask)

        def on_created(self, event):
            filepath = event.src_path
            print("New file to be converted: %s" %filepath)
            # Wait until the file is ready
            filesize = -1
            while filesize != os.path.getsize(filepath):
                filesize = os.path.getsize(filepath)
                sleep(.1)
            path = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            global instrument_name
            new_filename = '_'.join([instrument_name, filename])
            new_filepath = os.path.join(path, new_filename)
            try:
                os.rename(filepath, new_filepath)
            except FileExistsError:
                print("File exists: %s" %new_filepath)
                return
            filepath = new_filepath
            global file_queue
            file_queue.put(filepath)

    def log(self, *arg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

    def __init__(self, path, mask, recursive=False, shutdown_event=Event()):
        self.path = path
        self.recursive = recursive
        self.shutdown_event = shutdown_event
        self.observer = Observer()
        self.handler = self.FSEventHandler(mask)

    def start(self):
        self.observer.schedule(self.handler, self.path, recursive=self.recursive)
        self.observer.start()
        self.log('started watching', self.path)

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.log('stopped')

    def run(self):
        self.start()
        while not self.shutdown_event.is_set():
            try:
                sleep(.1)
            except KeyboardInterrupt:
                self.log('KeyboardInterrupt')
                self.shutdown_event.set()
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
        self.stop()

    def run_as_daemon(self):
        Thread(target=self.run).start()


async def create_sample_file_db_record(data):
    filename = data['filename']
    committed_length = data['committed_length']
    instrument = filename.split('_')[0]
    date = timestamp_from_filename(filename)
    utc_offset = timedelta(seconds=int(data['utc_offset']))
    title = data.get('title')
    description = data.get('description')
    mz_calibration = data.get('mz_calibration')
    attributes = data.get('attributes', {})
    await sio.emit(
            'sample_file_create',
            [{
                "filename": filename,
                "sample_file_name": title,
                "sample_file_description": description,
                "instrument": instrument,
                "datetime": date.isoformat(),
                "datetime_utc": (date - utc_offset).isoformat(),
                "length": committed_length,
                "range": data['range'],
                "mz_calibration": mz_calibration,
                "sample_file_attributes": attributes,
            }]
        )


async def streamer_processor(streamer):
    # Handlers
    async def handle_spec_data(data):
        filename = data['filename']
        spec_i = data['i']
        cache_item = cache.get(filename)
        if spec_i is None:
            # File finished
            zarr_sdk.finalize_signal_dataset({'value': data}, cache_item)
            data.update({
                'committed_length': cache_item.props['committed_length'],
                'range': cache_item.props['range'],
                'utc_offset': cache_item.props['utc_offset']
                })
            await create_sample_file_db_record(data)
        elif spec_i < 0:
            # New file
            try:
                cache_item = zarr_sdk.init_signal_dataset({'value': data})
            except FileExistsError:
                print("File exists: %s" %filename)
                return
            cache_item = AttrDict(cache_item)
            cache[data['filename']] = cache_item
        else:
            # New data to existing file
            zarr_sdk.update_signal_dataset({'value': data}, cache_item)
            
    async def handle_tps_data(data):
        filename = data['filename']
        spec_i = data['i']
        cache_item = cache.get(filename)
        if spec_i is None:
            # File finished
            pass
        elif spec_i < 0:
            # New file
            try:
                zarr_sdk.init_tps_dataset({'value': data}, cache_item)
            except FileExistsError:
                print("File exists: %s" %filename)
                return
        else:
            # New data to existing file
            zarr_sdk.update_tps_dataset({'value': data}, cache_item)

    # Main loop
    while not streamer.shutdown_event.is_set():
        try:
            spec_data = streamer.spec_queue.get_nowait()
            await handle_spec_data(spec_data)
            if hasattr(streamer, 'tps_queue'):
                tps_data = streamer.tps_queue.get()
                await handle_tps_data(tps_data)
        except Empty:
            await asyncio.sleep(.1)


async def run():
    host = os.environ['MASCOPE_PUBLIC_API_HOST']
    port = os.environ['MASCOPE_PUBLIC_PROXY_API_PORT']
    url = f"http://{host}:{port}"
    await sio.connect(url)
    while not shutdown_event.is_set():
        await asyncio.sleep(1)


load_dotenv()

cache = None
file_queue = Queue()
shutdown_event = Event()
sio = socketio.AsyncClient(logger=True)


if __name__ == '__main__':
    args = parse_cmd_args()

    instrument_name = args.get('instrument', 'unknown')

    streamer_type = args['streamer_type']
    if streamer_type == 'H5':
        streamer_class = H5Streamer
        file_mask = '*.h5'
    if streamer_type == 'Raw':
        streamer_class = RawStreamer
        file_mask = '*.raw'

    n_jobs = args.get('n_jobs', 1)
    cache = LRUDict(n_jobs)
    streamer_lock = Lock()
    streamers = [
        streamer_class(
            file_queue=file_queue,
            shutdown_event=shutdown_event,
            lock=streamer_lock,
        )
        for _ in range(n_jobs)
    ]
    loop = asyncio.get_event_loop()
    for streamer in streamers:
        streamer.start()
        loop.create_task(streamer_processor(streamer))

    source_path = args.get('data_pool_path', '.')
    fs_watcher = FSWatcher(
        path=source_path,
        mask=file_mask,
        shutdown_event=shutdown_event,
        )
    fs_watcher.run_as_daemon()


    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        shutdown_event.set()