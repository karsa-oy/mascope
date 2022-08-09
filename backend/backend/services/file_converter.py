from backend.lib.hardware.tofwerk.generator import H5Streamer
from backend.lib.struct import AttrDict, LRUDict
from file_io import zarr_sdk


import inspect

from multiprocessing import Event
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
            print("on_created: %s" %filepath)
            global streamer
            sleep(3)
            streamer.start_stream(filepath)

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
        zarr_sdk.finalize_signal_dataset({'value': data}, cache_item)
    elif spec_i < 0:
        cache_item = zarr_sdk.init_signal_dataset({'value': data})
        cache_item = AttrDict(cache_item)
        cache[data['filename']] = cache_item
    else:
        zarr_sdk.update_signal_dataset({'value': data}, cache_item)
        

def handle_tps_data(data):
    filename = data['filename']
    spec_i = data['i']
    cache_item = cache.get(filename)
    if spec_i is None:
        pass
    elif spec_i < 0:
        zarr_sdk.init_tps_dataset({'value': data}, cache_item)
    else:
        zarr_sdk.update_tps_dataset({'value': data}, cache_item)

def run():
    global streamer
    while not streamer.shutdown_event.is_set():
        try:
            spec_data = streamer.spec_queue.get(timeout=None)
            handle_spec_data(spec_data)
            tps_data = streamer.tps_queue.get()
            handle_tps_data(tps_data)
        except Empty:
            sleep(.1)


cache = LRUDict(1)
streamer = H5Streamer()
fs_watcher = FSWatcher(
    path='.',
    mask='*.h5',
    shutdown_event=streamer.shutdown_event,
    )


if __name__ == '__main__':
    fs_watcher.run_as_daemon()
    streamer.start()
    try:
        run()
    except KeyboardInterrupt:
        streamer.shutdown_event.set()