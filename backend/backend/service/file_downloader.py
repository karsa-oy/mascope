import argparse
import asyncio
import inspect
import os
import shutil

from dotenv import load_dotenv
from multiprocessing import Event, Queue
from queue import Empty
from threading import Thread
from time import sleep
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from lib.util import load_env_yaml


file_queue = Queue()
shutdown_event = Event()
target_path = None

class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, mask):
            if not isinstance(mask, list):
                mask = [mask, ]
            super().__init__(patterns=mask)

        def on_created(self, event):
            filepath = event.src_path
            print("New file to be downloaded: %s" %filepath)
            # Wait until the file is ready
            filesize = -1
            while True:
                while filesize != os.path.getsize(filepath):
                    filesize = os.path.getsize(filepath)
                    sleep(1)
                try:
                    os.rename(filepath, filepath)
                    break
                except PermissionError:
                    print("Cannot access file, retrying...")
                    sleep(1)
                    continue
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
        type=bool, required=False
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
    loop = asyncio.get_event_loop()

    file_mask = args.get('file_mask', '*')
    recursive = args.get('recursive', False)
    source_path = args['source_dir']
    target_path = args['target_dir']

    fs_watcher = FSWatcher(
        path=source_path,
        mask=file_mask,
        recursive=recursive,
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