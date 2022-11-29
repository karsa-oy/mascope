import argparse
import asyncio
import inspect
import os
import sys
import shutil
import glob
from dotenv import load_dotenv
from multiprocessing import Event, Queue
from queue import Empty
from threading import Thread
from time import sleep
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
from backend.service.lib.util import load_env_yaml


file_queue = Queue()
shutdown_event = Event()
target_path = None

class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, parent, path, mask, recursive=False):
            self.parent = parent
            self.path = path
            self.mask = mask
            self.recursive = recursive
            self.observer = Observer()
            if not isinstance(mask, list):
                mask = [mask, ]
            super().__init__(patterns=mask)

        def log(self, *arg):
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

        def start(self):
            self.observer.schedule(self, self.path, recursive=self.recursive)
            self.observer.start()
            self.log('started watching', self.path)

        def stop(self):
            self.observer.stop()
            self.observer.join()
            self.log('stopped')

        def on_created(self, event):
            filepath = event.src_path
            self.log("New file to be downloaded: %s" %filepath)
            # Wait until the file is ready
            filesize = -1
            while not self.parent.shutdown_event.is_set():
                new_filesize = os.path.getsize(filepath)
                if filesize != new_filesize:
                    filesize = new_filesize
                    sleep(2)
                    continue
                try:
                    os.rename(filepath, filepath)
                    break
                except PermissionError:
                    self.log("Cannot access file, retrying...")
                    sleep(2)
                    continue
            if not self.parent.shutdown_event.is_set():
                global file_queue
                file_queue.put(filepath)

        def run(self):
            self.start()
            while not self.parent.shutdown_event.is_set():
                try:
                    sleep(.5)
                except KeyboardInterrupt:
                    self.log('KeyboardInterrupt')
                    self.parent.shutdown_event.set()
                except Exception as e:
                    self.log(f"Exception {e.__class__.__name__}({str(e)})")
                    pass
            self.stop()


    class FSPingHandler():
        PING_INTERVAL = 3
        def __init__(self, parent, path, mask, recursive=False):
            self.parent = parent
            self.path = path
            self.mask = mask
            self.recursive = recursive

        def log(self, *arg):
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

        def walk(self, path='.', mask='*.*', recursive=False):
            if recursive:
                search_path = os.path.join(path, '**', mask)
            else:
                search_path = os.path.join(path, mask)
            return glob.glob(search_path, recursive=recursive)

        def start(self):
            self.log('started watching', self.path)

        def stop(self):
            self.log('stopped')

        def on_created(self, filelist):
            # Check for ready files in the filelist,
            # return a list of not-yet-ready files
            files_in_progress = []
            for filepath, filesize in filelist:
                new_filesize = os.path.getsize(filepath)
                if filesize != new_filesize:
                    files_in_progress.append([filepath, new_filesize])
                    continue
                try:
                    os.rename(filepath, filepath)
                    global file_queue
                    self.log(f"Processing {filepath}")
                    file_queue.put(filepath)
                except PermissionError:
                    self.log(f"Cannot access file {filepath}, retrying...")
                    files_in_progress.append([filepath, new_filesize])
                    continue
            return files_in_progress

        def run(self):
            self.start()
            files = self.walk(self.path, self.mask, self.recursive)
            new_files = []
            while not self.parent.shutdown_event.is_set():
                try:
                    sleep(self.PING_INTERVAL)
                    latest_files = self.walk(self.path, self.mask, self.recursive)
                    new_files.extend([[path, -1] for path in set(latest_files).difference(files)])
                    files = latest_files
                    new_files = self.on_created(new_files)
                except KeyboardInterrupt:
                    self.log('KeyboardInterrupt')
                    self.parent.shutdown_event.set()
                except Exception as e:
                    self.log(f"Exception {e.__class__.__name__}({str(e)})")
                    pass
            self.stop()


    def log(self, *arg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

    def __init__(self, path, mask, recursive=False, ping=False, shutdown_event=Event()):
        assert os.path.isdir(path), f"{path} is missing"
        self.shutdown_event = shutdown_event
        if ping:
            self.handler = self.FSPingHandler(self, path, mask, recursive)
        else:
            self.handler = self.FSEventHandler(self, path, mask, recursive)

    def run_as_daemon(self):
        Thread(target=self.handler.run).start()


def parse_cmd_args():
    """
    Parse command line arguments
    ------------------------------
    Return dict
    Default argument values: see default_args.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c", "--config",
        help="path to yaml config file",
        type=str, required=False
    )
    parser.add_argument(
        "-m", "--file_mask",
        help="filename mask",
        type=str, required=False
    )
    parser.add_argument(
        "-r", "--recursive",
        help="recursive",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "-s", "--source_dir",
        help="source directory",
        type=str, required=False
    )
    parser.add_argument(
        "-t", "--target_dir",
        help="target directory",
        type=str, required=False
    )
    parser.add_argument(
        "-p", "--ping",
        help="ping source directory for new samples (alt to filesystem event)",
        action='store_true',
        default=False
    )
    all_args = parser.parse_args()
    cmdline_args = {}
    for arg in vars(all_args):
        if vars(all_args)[arg] is None:
            continue
        cmdline_args[arg] = vars(all_args)[arg]
    file_args = {}
    if all_args.config:
        # service config may be defined in yaml file
        file_args = load_env_yaml(all_args.config)
    return {
        **file_args,
        **cmdline_args
        }


async def main():
    global file_queue
    global shutdown_event
    global target_path
    while not shutdown_event.is_set():
        try:
            file_to_download = file_queue.get_nowait()
            filename = os.path.basename(file_to_download)
            shutil.move(file_to_download, os.path.join(target_path, filename))
        except Empty:
            await asyncio.sleep(1)


def run():
    global file_queue
    global shutdown_event
    global target_path

    args = parse_cmd_args()
    print(args)
    loop = asyncio.get_event_loop()

    source_path = args['source_dir']
    file_mask = args.get('file_mask', '*')
    target_path = args['target_dir']
    recursive = args['recursive']
    ping = args['ping']

    fs_watcher = FSWatcher(
        path=source_path,
        mask=file_mask,
        recursive=recursive,
        ping=ping,
        shutdown_event=shutdown_event,
        )
    fs_watcher.run_as_daemon()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        shutdown_event.set()
    except Exception as e:
        print(e)
        shutdown_event.set()


if __name__ == '__main__':
    load_dotenv()
    run()