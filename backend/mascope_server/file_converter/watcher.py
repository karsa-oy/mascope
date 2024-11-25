import glob
import os
from threading import Event, Thread
from time import sleep

from mascope_runtime import MascopeRuntimeModule

runtime = MascopeRuntimeModule("file-converter")


class FSWatcher(Thread):
    def __init__(
        self,
        path,
        pattern,
        file_queue,
        interval=1,
        shutdown_event=Event(),
        recursive=False,
    ):
        Thread.__init__(self)
        self.log = runtime.logger.bind(key=self.name)
        self.log.info(
            f"Initializing filesystem watcher ({self.name}) with pattern {pattern}"
        )
        assert os.path.isdir(path), f"{path} is missing"
        self.path = path
        self.pattern = pattern
        self.file_queue = file_queue
        self.interval = interval
        self.shutdown_event = shutdown_event
        self.recursive = recursive

    def walk(self):
        if self.recursive:
            search_path = os.path.join(self.path, "**", self.pattern)
        else:
            search_path = os.path.join(self.path, self.pattern)
        return glob.glob(search_path, recursive=self.recursive)

    def on_created(self, filelist):
        # Check for ready files in the filelist,
        # return a list of not-yet-ready files
        files_in_progress = []
        for filepath, filesize in filelist:
            try:
                new_filesize = os.path.getsize(filepath)
            except FileNotFoundError:
                # File was deleted, move on
                continue
            if filesize != new_filesize:
                files_in_progress.append([filepath, new_filesize])
                continue
            try:
                os.rename(filepath, filepath)
                runtime.logger.info(f"Processing {filepath}")
                self.file_queue.put(filepath)
            except PermissionError:
                runtime.logger.error(f"Cannot access file {filepath}, retrying...")
                files_in_progress.append([filepath, new_filesize])
                continue
        return files_in_progress

    def run(self):
        runtime.logger.info(f"started watching {self.path}")
        files = self.walk()
        new_files = []
        while not self.shutdown_event.is_set():
            try:
                sleep(self.interval)
                latest_files = self.walk()
                new_files.extend(
                    [[path, -1] for path in set(latest_files).difference(files)]
                )
                files = latest_files
                new_files = self.on_created(new_files)
            except KeyboardInterrupt:
                runtime.logger.critical("KeyboardInterrupt")
                self.shutdown_event.set()
            except Exception as e:
                runtime.logger.exception(e)
        runtime.logger.info("stopped")
