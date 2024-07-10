import glob
import inspect
import os
from threading import Event, Thread
from time import sleep

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

import mascope_runtime as runtime

logger = runtime.logger.service('backend')

class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, parent, path, patterns, recursive=False):
            self.parent = parent
            self.path = path
            self.recursive = recursive
            self.observer = Observer()
            super().__init__(patterns=patterns)

        def start(self):
            self.observer.schedule(self, self.path, recursive=self.recursive)
            self.observer.start()
            logger.info(f"started watching {self.path}")

        def stop(self):
            self.observer.stop()
            self.observer.join()
            logger.info("stopped")

        def on_created(self, event):
            filepath = event.src_path
            logger.info(f"Processing {filepath}")
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
                    logger.error(f"Cannot access {filepath}, retrying...")
                    sleep(2)
                    continue
            if not self.parent.shutdown_event.is_set():
                self.parent.file_queue.put(filepath)

        def run(self):
            self.start()
            while not self.parent.shutdown_event.is_set():
                try:
                    sleep(0.5)
                except KeyboardInterrupt:
                    logger.critical("KeyboardInterrupt")
                    self.parent.shutdown_event.set()
                except Exception as e:
                    logger.error(f"Exception {e.__class__.__name__}({str(e)})")
                    pass
            self.stop()

    class FSPingHandler:
        PING_INTERVAL = 3

        def __init__(self, parent, path, patterns, recursive=False):
            self.parent = parent
            self.path = path
            self.patterns = patterns
            self.recursive = recursive

        def walk(self, path=".", pattern="*.*", recursive=False):
            if recursive:
                search_path = os.path.join(path, "**", pattern)
            else:
                search_path = os.path.join(path, pattern)
            return glob.glob(search_path, recursive=recursive)

        def start(self):
            logger.info("started watching", self.path)

        def stop(self):
            logger.info("stopped")

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
                    logger.info(f"Processing {filepath}")
                    self.parent.file_queue.put(filepath)
                except PermissionError:
                    logger.error(f"Cannot access file {filepath}, retrying...")
                    files_in_progress.append([filepath, new_filesize])
                    continue
            return files_in_progress

        def run(self):
            self.start()
            files = self.walk(self.path, self.patterns[0], self.recursive)
            new_files = []
            while not self.parent.shutdown_event.is_set():
                try:
                    sleep(self.PING_INTERVAL)
                    latest_files = self.walk(self.path, self.mask, self.recursive)
                    new_files.extend(
                        [[path, -1] for path in set(latest_files).difference(files)]
                    )
                    files = latest_files
                    new_files = self.on_created(new_files)
                except KeyboardInterrupt:
                    logger.critical("KeyboardInterrupt")
                    self.parent.shutdown_event.set()
                except Exception as e:
                    logger.error(f"Exception {e.__class__.__name__}({str(e)})")
                    pass
            self.stop()

    def __init__(
        self,
        path,
        patterns,
        file_queue,
        recursive=False,
        ping=False,
        shutdown_event=Event(),
    ):
        assert os.path.isdir(path), f"{path} is missing"
        self.shutdown_event = shutdown_event
        self.file_queue = file_queue
        if ping:
            self.handler = self.FSPingHandler(self, path, patterns, recursive)
        else:
            self.handler = self.FSEventHandler(self, path, patterns, recursive)

    def run_as_daemon(self):
        Thread(target=self.handler.run).start()
