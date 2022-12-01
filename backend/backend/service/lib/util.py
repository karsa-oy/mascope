import os
import re
import yaml
import inspect
import glob
from threading import Thread, Event
from time import sleep
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


def load_env_yaml(yaml_file):
    env_pattern = re.compile(r".*?\${(.*?)}.*?")
    def env_constructor(loader, node):
        value = loader.construct_scalar(node)
        for group in env_pattern.findall(value):
            value = value.replace(f"${{{group}}}", os.environ.get(group))
        return value
    yaml.add_implicit_resolver("!pathex", env_pattern)
    yaml.add_constructor("!pathex", env_constructor)
    with open(yaml_file, 'r') as f:
        res = yaml.load(f.read(), Loader=yaml.FullLoader)
    return res

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
            self.log(f"Processing {filepath}")
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
                    self.log(f"Cannot access {filepath}, retrying...")
                    sleep(2)
                    continue
            if not self.parent.shutdown_event.is_set():
                self.parent.file_queue.put(filepath)

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
                    self.log(f"Processing {filepath}")
                    self.parent.file_queue.put(filepath)
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

    def __init__(self, path, mask, file_queue, recursive=False, ping=False, shutdown_event=Event()):
        assert os.path.isdir(path), f"{path} is missing"
        self.shutdown_event = shutdown_event
        self.file_queue = file_queue
        if ping:
            self.handler = self.FSPingHandler(self, path, mask, recursive)
        else:
            self.handler = self.FSEventHandler(self, path, mask, recursive)

    def run_as_daemon(self):
        Thread(target=self.handler.run).start()
