import inspect
import os

from backend.lib.hardware.tofwerk.generator import H5Streamer
from backend.lib.hardware.orbitrap.generator import RawStreamer
from backend.lib.struct import AttrDict, LRUDict
from backend.lib.util import parse_cmd_args
from file_io import zarr_sdk

from multiprocessing import Event, Queue
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


def handle_spec_data(data):
    filename = data['filename']
    spec_i = data['i']
    cache_item = cache.get(filename)
    if spec_i is None:
        # File finished
        zarr_sdk.finalize_signal_dataset({'value': data}, cache_item)
    elif spec_i < 0:
        # New file
        cache_item = zarr_sdk.init_signal_dataset({'value': data})
        cache_item = AttrDict(cache_item)
        cache[data['filename']] = cache_item
    else:
        # New data to existing file
        zarr_sdk.update_signal_dataset({'value': data}, cache_item)
        
def handle_tps_data(data):
    filename = data['filename']
    spec_i = data['i']
    cache_item = cache.get(filename)
    if spec_i is None:
        # File finished
        pass
    elif spec_i < 0:
        # New file
        zarr_sdk.init_tps_dataset({'value': data}, cache_item)
    else:
        # New data to existing file
        zarr_sdk.update_tps_dataset({'value': data}, cache_item)

def streamer_processor(streamer):
    while not streamer.shutdown_event.is_set():
        try:
            spec_data = streamer.spec_queue.get(timeout=None)
            handle_spec_data(spec_data)
            if hasattr(streamer, 'tps_queue'):
                tps_data = streamer.tps_queue.get()
                handle_tps_data(tps_data)
        except Empty:
            sleep(.1)


def run():
    while not shutdown_event.is_set():
        sleep(1)


cache = None
file_queue = Queue()
shutdown_event = Event()

if __name__ == '__main__':
    args = parse_cmd_args()
    print(args)

    streamer_type = args['streamer_type']
    if streamer_type == 'H5':
        streamer_class = H5Streamer
        file_mask = '*.h5'
    if streamer_type == 'Raw':
        streamer_class = RawStreamer
        file_mask = '*.raw'

    n_jobs = args.get('n_jobs', 1)
    cache = LRUDict(n_jobs)
    streamers = [
        streamer_class(
            file_queue=file_queue,
            shutdown_event=shutdown_event,
        )
        for _ in range(n_jobs)
    ]
    
    for streamer in streamers:
        streamer.start()
        Thread(target=streamer_processor, args=(streamer,)).start()

    source_path = args.get('data_pool_path', '.')
    fs_watcher = FSWatcher(
        path=source_path,
        mask=file_mask,
        shutdown_event=shutdown_event,
        )
    fs_watcher.run_as_daemon()
    
    try:
        run()
    except KeyboardInterrupt:
        streamer.shutdown_event.set()