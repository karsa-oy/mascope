import argparse
from ntpath import basename
import os
import time
import re
from shutil import SameFileError, copy2
from multiprocessing import Event, Queue
from queue import Empty
# from karsalib.struct import FSWatcher
# from karsalib.logging import parent_func_name
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import inspect


MOVE_TIMEOUT = 10   # seconds without access before moving sample to target dir

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="source data pool path to watch", type=str, required=True)
    parser.add_argument("-t", "--target", help="target data pool path to copy to", type=str, required=True)
    parser.add_argument("-m", "--mask", help="source file mask to watch", type=str, required=True)
    parser.add_argument("-mt", "--move_timeout", help="seconds without access before moving sample to target dir", type=int, default=10)
    return parser.parse_args()


def parent_func_name():
    return inspect.stack()[2][3]


class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, client, mask):
            self.client = client
            if not isinstance(mask, list):
                mask = [mask, ]
            super().__init__(patterns=mask)

        def log(self, *arg):
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

        def on_created(self, event):
            try:
                self.client.on_filesystem_object_created(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_modified(self, event):
            try:
                self.client.on_filesystem_object_modified(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_deleted(self, event):
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_moved(self, event):
            try:
                self.client.on_filesystem_object_created(event.dest_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

    def log(self, *arg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

    def __init__(self, client, target_attrs, recursive=False):
        self.client = client
        self.target_attrs = target_attrs
        self.recursive = recursive
        self.observer = Observer()
        self.handler = self.FSEventHandler(self.client, self.target_attrs['mask'])

    def start(self):
        self.observer.schedule(self.handler, self.target_attrs['path'], recursive=self.recursive)
        self.observer.start()
        self.log('started watching', self.target_attrs)

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.log('stopped')

    def run(self):
        self.start()
        while not self.client.shutdown_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.log('KeyboardInterrupt')
                self.client.shutdown_event.set()
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
        self.stop()

    def run_as_daemon(self):
        Thread(target=self.run).start()



class SampleMover():
    def log(self, *arg):
        print(f"[{self.__class__.__name__}.{parent_func_name()}]", *arg)

    def __init__(self, src, target, mask):
        self.shutdown_event = Event()
        self.target_dir = target
        self.jobs = Queue()
        self.watcher = FSWatcher(client=self,
                        target_attrs={'path': src, 'mask': mask},
                        recursive=True)

    def on_filesystem_object_created(self, fname):
        self.log(fname)
        # Wait until the file is ready
        filesize = -1
        while True:
            while filesize != os.path.getsize(fname):
                filesize = os.path.getsize(fname)
                time.sleep(1)
            try:
                os.rename(fname, fname)
                break
            except PermissionError:
                print("PermissionError, retrying...")
                time.sleep(1)
        self.jobs.put(fname)

    def on_filesystem_object_deleted(self, path):
        self.log(path)

    def seconds_since_last_access(self, fname):
        return time.time() - os.stat(fname).st_atime

    def get_date_from_name(self, fname):
        patterns = [
            r'.*(\d{4}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).*',
            r'.*(\d{4})(\d{2})(\d{2})[- _](\d{2})(\d{2})[- _].*',
        ]
        for p in patterns:
            try:
                dt = re.findall(p, basename(fname))[0]
                dt_len = len(dt)
                if dt_len == 5 or dt_len == 6:
                    return '.'.join(dt[0:3])
            except IndexError:
                pass
        return None

    def copy(self, fname, fdate):
        dst_dir = os.path.join(self.target_dir, fdate)
        if not os.path.isdir(dst_dir):
            os.mkdir(dst_dir)
        dst_fname = os.path.join(dst_dir, basename(fname))
        copy2(fname, dst_fname)
        self.log(dst_fname)

    def run_until_complete(self, args):
        try:
            while not self.shutdown_event.is_set():
                time.sleep(2)
                fname = None
                try:
                    fname = self.jobs.get_nowait()
                    fdate = self.get_date_from_name(fname)
                    if not fdate:
                        self.log(f"{fname} skipped: invalid sample name")
                        continue
                    # self.log(fname)
                    if self.seconds_since_last_access(fname) < args.move_timeout:
                        self.jobs.put(fname)
                        # self.log(fname, 'back')
                        continue
                    self.copy(fname, fdate)
                except Empty:
                    continue
                except FileNotFoundError:
                    continue
                except SameFileError:
                    continue
        except KeyboardInterrupt as e:
            self.log(f"{e.__class__.__name__}({str(e)})")
        except Exception as e:
            self.log(f"{e.__class__.__name__}({str(e)})")
        finally:
            self.shutdown_event.set()

def run():
    args = parse_args()
    assert  all(map(lambda d: os.path.isdir(d), [args.source, args.target])), \
            "Invalid source or target folder"
    mover = SampleMover(args.source, args.target, args.mask)
    mover.watcher.run_as_daemon()
    mover.run_until_complete(args)



if __name__ == '__main__':
    run()
