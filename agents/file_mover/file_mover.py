import argparse
import inspect
import os
import time
from multiprocessing import Event, Queue
from ntpath import basename
from queue import Empty
from shutil import SameFileError, copy2

from threading import Thread

import watchdog
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

MOVE_TIMEOUT = 10  # seconds without access before moving sample to target dir


def parse_args() -> argparse.Namespace:
    """Parse command line arguments

    :return: Parsed arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--source", help="source data pool path to watch", type=str, required=True
    )
    parser.add_argument(
        "-t",
        "--target",
        help="target data pool path to copy to",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-m", "--mask", help="source file mask to watch", type=str, required=True
    )
    parser.add_argument(
        "-mt",
        "--move_timeout",
        help="seconds without access before moving sample to target dir",
        type=int,
        default=MOVE_TIMEOUT,
    )
    return parser.parse_args()


def parent_func_name() -> str:
    """Return the name of a parent function calling a class method

    :return: Parent function name
    :rtype: str
    """
    return inspect.stack()[2][3]


class FSWatcher:
    """Watch for file system events in a specified directory"""

    class FSEventHandler(PatternMatchingEventHandler):
        """File system event handler

        Implement callbacks for file system events.

        :param PatternMatchingEventHandler: Event handler from the watchdog package
        :type PatternMatchingEventHandler: watchdig.events.PatternMatchingEventHandler
        """

        def __init__(self, client, mask):
            self.client = client
            if not isinstance(mask, list):
                mask = [
                    mask,
                ]
            super().__init__(patterns=mask)

        def log(self, *arg) -> None:
            """Print log message"""
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

        def on_created(self, event: watchdog.events.FileSystemEvent) -> None:
            """New file created

            :param event: Filesystem event
            :type event: watchdog.events.FileSystemEvent
            """
            try:
                self.client.on_filesystem_object_created(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")

        def on_modified(self, event: watchdog.events.FileSystemEvent) -> None:
            """File modified

            :param event: Filesystem event
            :type event: watchdog.events.FileSystemEvent
            """
            try:
                self.client.on_filesystem_object_modified(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")

        def on_deleted(self, event: watchdog.events.FileSystemEvent) -> None:
            """File deleted

            :param event: Filesystem event
            :type event: watchdog.events.FileSystemEvent
            """
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")

        def on_moved(self, event: watchdog.events.FileSystemEvent) -> None:
            """File moved

            :param event: Filesystem event
            :type event: watchdog.events.FileSystemEvent
            """
            try:
                self.client.on_filesystem_object_created(event.dest_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")

    def log(self, *arg) -> None:
        """Print a log message"""
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

    def __init__(self, client, target_attrs, recursive=False):
        self.client = client
        self.target_attrs = target_attrs
        self.recursive = recursive
        self.observer = Observer()
        self.handler = self.FSEventHandler(self.client, self.target_attrs["mask"])

    def start(self) -> None:
        """Start watching.

        Start `FSEventHandler`
        """
        self.observer.schedule(
            self.handler, self.target_attrs["path"], recursive=self.recursive
        )
        self.observer.start()
        self.log("started watching", self.target_attrs)

    def stop(self) -> None:
        """Stop watching.

        Stop `FSEventHandler`
        """
        self.observer.stop()
        self.observer.join()
        self.log("stopped")

    def run(self) -> None:
        """Main loop

        Start `FSEventHandler` and do nothing.
        """
        self.start()
        while not self.client.shutdown_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.log("KeyboardInterrupt")
                self.client.shutdown_event.set()
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
        self.stop()

    def run_as_daemon(self):
        Thread(target=self.run).start()


class SampleMover:
    """Watch for new files matching a specified `mask` in `source` directory, copy into
    `target` directory after file has not been accessed for specified timeout period.
    """

    def log(self, *arg) -> None:
        """Print log message"""
        print(f"[{self.__class__.__name__}.{parent_func_name()}]", *arg)

    def __init__(self, src, target, mask):
        self.shutdown_event = Event()
        self.target_dir = target
        self.jobs = Queue()
        self.watcher = FSWatcher(
            client=self, target_attrs={"path": src, "mask": mask}, recursive=True
        )

    def on_filesystem_object_created(self, fname: str) -> None:
        """Callback on file created.

        First wait while filesize is changing. Then check file access
        by dummy rename operation. Finally, put file into `self.jobs` queue.

        :param fname: File path
        :type fname: str
        """
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

    def seconds_since_last_access(self, fname: str) -> float:
        """Count the seconds since the file was last accessed

        :param fname: Path of the file
        :type fname: str
        :return: Seconds since last access
        :rtype: float
        """
        return time.time() - os.stat(fname).st_atime

    def copy(self, fname: str) -> None:
        """Copy file into target directory

        :param fname: Path of the file to copy
        :type fname: str
        """
        dst_fname = os.path.join(self.target_dir, basename(fname))
        copy2(fname, dst_fname)
        self.log(dst_fname)

    def run_until_complete(self, args):
        """Main loop

        :param args: Arguments
        :type args: argparse.Namespace
        """
        try:
            while not self.shutdown_event.is_set():
                time.sleep(2)
                fname = None
                try:
                    fname = self.jobs.get_nowait()
                    # self.log(fname)
                    if self.seconds_since_last_access(fname) < args.move_timeout:
                        self.jobs.put(fname)
                        # self.log(fname, 'back')
                        continue
                    self.copy(fname)
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


def run() -> None:
    """Main function of the application

    Start `SampleMover` thread and wait until it finishes
    """
    args = parse_args()
    assert all(
        map(lambda d: os.path.isdir(d), [args.source, args.target])
    ), "Invalid source or target folder"
    mover = SampleMover(args.source, args.target, args.mask)
    mover.watcher.run_as_daemon()
    mover.run_until_complete(args)


if __name__ == "__main__":
    run()
