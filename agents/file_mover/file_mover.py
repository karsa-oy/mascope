import inspect
import os
import time
import sys
import textwrap

from multiprocessing import Event, Queue
from ntpath import basename
from queue import Empty
from shutil import SameFileError, copy2
from threading import Thread

import watchdog

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from mascope_runtime import Runtime


# check if we are running in a pyinstaller bundle
bundled = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def mkdir(*args):
    path = os.path.join(*args)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


# default configuration
# created in production as an initial
# template for users to modify
default_config = textwrap.dedent(
    """\
    [meta]
    # meta
    log_level = 'info'
    # settings
    description = "The default runtime env"
    api_port = 8090
    filestore = './filestore'

    [file-mover]
    # meta
    log_level = 'info'
    log_path = './logs'
    # settings
    mask = '*.raw'
    timeout = 10
    source = './data'
    target = './filestreams'
    """
)


if bundled:
    # prod mode
    # set MASCOPE_PATH as %AppData%\Mascope\TOF_Agent
    mascope_path = mkdir(os.environ["APPDATA"], "Mascope", "FileMover")
    os.environ.setdefault("MASCOPE_PATH", mascope_path)
    # setup runtime environment
    env_path = mkdir(mascope_path, "runtime", "env", "prod")
    data_path = mkdir(env_path, "data")
    mkdir(env_path, "logs")
    # init config files if they don't exists
    config_paths = [
        os.path.join(env_path, "base.mascope.toml"),
        os.path.join(env_path, "prod.mascope.toml"),
    ]
    for path in config_paths:
        if not os.path.exists(path):
            with open(path, "w") as file:
                file.write(default_config)
    # initialize the runtime in production mode
    runtime = Runtime("file-mover", env="prod", mode="prod", path=mascope_path)
else:
    # dev mode
    # runtime state inherited from the CLI
    runtime = Runtime("file-mover")


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
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")

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
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")

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
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")

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
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")

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
        runtime.logger.info(f"started watching {self.target_attrs['path']}")

    def stop(self) -> None:
        """Stop watching.

        Stop `FSEventHandler`
        """
        self.observer.stop()
        self.observer.join()
        runtime.logger.info("stopped")

    def run(self) -> None:
        """Main loop

        Start `FSEventHandler` and do nothing.
        """
        self.start()
        while not self.client.shutdown_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                runtime.logger.critical("KeyboardInterrupt")
                self.client.shutdown_event.set()
            except Exception as e:
                runtime.logger.critical(f"Exception {e.__class__.__name__}({str(e)})")
                pass
        self.stop()

    def run_as_daemon(self):
        Thread(target=self.run).start()


class SampleMover:
    """Watch for new files matching a specified `mask` in `source` directory, copy into
    `target` directory after file has not been accessed for specified timeout period.
    """

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
        runtime.logger.info(fname)
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
                runtime.logger.error("PermissionError, retrying...")
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
        runtime.logger.info(dst_fname)

    def run_until_complete(self):
        """Main loop

        :param config: Configuration
        :type config: MascopeConfig
        """
        try:
            while not self.shutdown_event.is_set():
                time.sleep(2)
                fname = None
                try:
                    fname = self.jobs.get_nowait()
                    runtime.logger.debug(fname)
                    if self.seconds_since_last_access(fname) < runtime.config.timeout:
                        self.jobs.put(fname)
                        runtime.logger.debug(fname, "back")
                        continue
                    self.copy(fname)
                except Empty:
                    continue
                except FileNotFoundError:
                    continue
                except SameFileError:
                    continue
        except KeyboardInterrupt as e:
            runtime.logger.critical(f"{e.__class__.__name__}({str(e)})")
        except Exception as e:
            runtime.logger.critical(f"{e.__class__.__name__}({str(e)})")
        finally:
            self.shutdown_event.set()


def run() -> None:
    """Main function of the application

    Start `SampleMover` thread and wait until it finishes
    """
    assert all(
        map(
            lambda d: os.path.isdir(d),
            [runtime.config.source, runtime.config.target],
        )
    ), "Invalid source or target folder"
    mover = SampleMover(
        runtime.config.source, runtime.config.target, runtime.config.mask
    )
    mover.watcher.run_as_daemon()
    mover.run_until_complete()


if __name__ == "__main__":
    run()
