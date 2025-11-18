import glob
import os
from threading import Event, Thread
from time import sleep

from .runtime import runtime


class FSWatcher(Thread):
    def __init__(
        self,
        path,
        pattern,
        file_queue,
        interval=1,
        shutdown_event=Event(),
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

    def walk(self) -> list[str]:
        """Find all files matching the pattern in the path.
        This method is case-insensitive and will find files with both lower and upper case extensions.

        :return: List of files matching the pattern in the path.
        :rtype: list[str]
        """
        search_path_lower = os.path.join(self.path, self.pattern.lower())
        search_path_upper = os.path.join(self.path, self.pattern.upper())
        files = glob.glob(search_path_lower)
        files.extend(glob.glob(search_path_upper))
        return files

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
