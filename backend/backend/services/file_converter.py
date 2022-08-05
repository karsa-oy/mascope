from backend.lib.hardware.tofwerk.generator import H5Streamer
import inspect
import os
import re

from backend.lib.struct import AttrDict, CacheQ
from backend.lib.util import generate_unique_key, get_client_notification_context

from multiprocessing import Event, Lock
from ntpath import basename, dirname
from threading import Thread
from time import sleep
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, mask, client):
            self.client = client
            if not isinstance(mask, list):
                mask = [mask, ]
            super().__init__(patterns=mask)

        def on_created(self, event):
            def _create_generator_request(data):
                def is_reimport_request(fdata):
                    return all([fdata.get('props'), fdata.get('attrs')])

                kwargs = get_client_notification_context(data)
                rdata = {**kwargs, 'files': []}
                for v in data['value']:
                    fname = v['filename']
                    if is_reimport_request(v):
                        rdata['files'].append(v)
                    else:
                        fname = v.pop('filename')
                        path = v.pop('path', None)    # path normally does not come with batch import
                        try:
                            fprops = get_src_data(path, fname)
                        except Exception as e:
                            raise
                        # attrs normally contain sci data coming along with the sample
                        rdata['files'].append({**fprops, 'attrs': v})
                return rdata
            
            def get_src_data(path, fname):
                def get_h5_datetime():
                    # returns ('YYYY.mm.dd', 'HH:MM:SS') for TOF h5 samples
                    dt_regex = r'.*(\d{4}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).*\.h5'
                    dt = re.findall(dt_regex, fname)[0]
                    return '.'.join(dt[:3]), ':'.join(dt[3:])

                def get_raw_datetime():
                    # returns ('YYYY.mm.dd', 'HH:MM') for Orbi raw samples
                    dt_regex = r'^(\d{8}).(\d{4}).*\.raw'
                    d, t = re.findall(dt_regex, fname)[0]
                    return '.'.join([d[:4], d[4:6], d[6:]]), ':'.join([t[:2], t[2:]])

                try:
                    fdate, ftime = get_h5_datetime()
                except IndexError:
                    fdate, ftime = get_raw_datetime()
                full_fname = os.path.join(path, fname)
                size = round((os.path.getsize(full_fname)) / 2**20, 2)  # in MB
                return {'filename': fname,
                        'path': path,
                        'props': {'filesize': size, 'datetime': f'{fdate} {ftime}'},
                    }
            filename = basename(event.src_path)
            raw_sample_data = {
                'name': 'raw_import',
                'value': [
                    {'filename': filename, 'path': dirname(event.src_path), },
                ],
                'request_id': generate_unique_key(),
                # unique client_room - for a new transit request not to replace prev.one
                'client_room': generate_unique_key(),
            }
            print("on_created: %s" %filename)
            # sleep(3)   # let file object to be created properly
            self.client.requests.cache_put(raw_sample_data)

    def log(self, *arg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

    def __init__(self, path, mask, client, recursive=False, shutdown_event=Event()):
        self.path = path
        self.client = client
        self.recursive = recursive
        self.shutdown_event = shutdown_event
        self.observer = Observer()
        self.handler = self.FSEventHandler(mask, client)

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


if __name__ == '__main__':
    shutdown_event = Event()

    client = AttrDict(
        in_progress=None,
        instrument_name="testiInstrumentti",
        lock=Lock(),
        requests=CacheQ('client_room'),
        responses=CacheQ('client_room/filename'),
        shutdown_event=shutdown_event,
        target_data_pool_path='./target_data_pool_path',
        )
    streamer = H5Streamer(client)

    fs_watcher = FSWatcher(
        path='.',
        mask='*.h5',
        client=client,
        shutdown_event=shutdown_event,
    )

    fs_watcher.run_as_daemon()
    streamer.run()

    while not shutdown_event.is_set():
        try:
            sleep(.1)
        except KeyboardInterrupt:
            shutdown_event.set()