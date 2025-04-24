import os
import time
import shutil
import sys
import textwrap

from multiprocessing import Event, Queue
from queue import Empty
from threading import Thread

import watchdog

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from mascope_runtime import Runtime
from mascope_sdk import api_post_file


# default configuration
# created in production as an initial
# template for users to modify
DEFAULT_CONFIG = textwrap.dedent(
    """\
    [meta]
    # meta
    log_level = 'info'
    # settings
    description = "The default runtime env"
    api_port = 8090
    filestore = './filestore'

    [file-agent]
    # meta
    log_level = 'info'
    log_path = './logs'
    color = "purple"
    # settings
    mask = '*.raw'
    timeout = 3
    source = './data'
    host = 'localhost'
    access_token = ''
    """
)

FILE_UPLOAD_SIZE_LIMIT = 2.5 * 1024**3  # 2.5 GB
HOST = None
PORT = None
URL = None
SHUTDOWN_EVENT = Event()

runtime = None  # pylint: disable=invalid-name


def process_file_upload(filepath: str) -> None:
    """Process file upload

    :param filepath: Full path to the file to be uploaded
    :type filepath: str
    """
    try:
        upload_sample_file(filepath)
    except Exception as e:  # pylint: disable=broad-except
        runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")
        # Move failed file into a separate directory
        failed_dir = mkdir(runtime.config.source, "failed_uploads")
        failed_filepath = os.path.join(failed_dir, os.path.basename(filepath))
        shutil.copyfile(filepath, failed_filepath)
        runtime.logger.debug(f"Copied failed file to {failed_filepath}")


def upload_sample_file(filepath: str) -> None:
    """Upload the acquired file to Mascope server using Mascope API

    :param filepath: Full path to the file to be uploaded
    :type filepath: str
    :raises Exception: Raises an exception if the request fails (status code != 200)
    """

    # Validate file before upload request
    # file extension
    file_ext = os.path.splitext(filepath)[1].lower()
    mask_ext = os.path.splitext(runtime.config.mask)[1].lower()
    if file_ext != mask_ext:
        raise ValueError(f"{file_ext} is not an allowed file extension!")
    # file size
    file_size = os.stat(filepath).st_size
    if file_size > FILE_UPLOAD_SIZE_LIMIT:
        raise ValueError(
            (
                f"File size ({round(file_size / (1024**3), 1)} GB) exceeds the maximum",
                f"allowed size ({FILE_UPLOAD_SIZE_LIMIT / (1024**3)} GB)",
            )
        )

    # Make file upload request
    runtime.logger.debug(f"Making an upload request to {URL} for file {filepath}")
    resp = api_post_file(
        url=URL,
        path="sample/files/upload",
        access_token=runtime.config.access_token,
        filepath=filepath,
        service_name="file-agent",
    )

    if resp is not None:
        runtime.logger.info(
            f"File upload of file {os.path.basename(filepath)} succeeded!"
        )
    else:
        raise RuntimeError(f"File upload failed for file {os.path.basename(filepath)}")


def mkdir(*args: tuple) -> str:
    """
    Creates a directory at the specified path if it does not already exist.

    :param args: Components of the path to be joined.
    :type args: tuple
    :return: The path of the created directory.
    :rtype: str
    """

    path = os.path.join(*args)
    os.makedirs(path, exist_ok=True)
    return path


def initialize() -> None:
    """Initialize the application and runtime depending on dev/prod mode

    If in prod mode, check if runtime directory structure exists, and create if not.

    :return: Return nothing
    :rtype: None
    """
    global runtime  # pylint: disable=global-statement
    # check if we are running in a pyinstaller bundle
    bundled = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    if bundled:
        # prod mode
        # set MASCOPE_PATH as %AppData%\Mascope\FileAgent
        mascope_path = mkdir(os.environ["APPDATA"], "Mascope", "FileAgent")
        os.environ.setdefault("MASCOPE_PATH", mascope_path)
        # setup runtime environment
        env_path = mkdir(mascope_path, ".runtime", "env", "prod")
        mkdir(env_path, "logs")
        mkdir(env_path, "data")
        # init config files if they don't exists
        config_paths = [
            os.path.join(env_path, "base.mascope.toml"),
            os.path.join(env_path, "prod.mascope.toml"),
        ]
        for path in config_paths:
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as file:
                    file.write(DEFAULT_CONFIG)
        # initialize the runtime in production mode
        runtime = Runtime("file-agent", env="prod", mode="prod", path=mascope_path)
    else:
        # dev mode
        # runtime state inherited from the CLI
        runtime = Runtime("file-agent")


class FileSystemWatcher:
    """Watch for file system events in a specified directory"""

    class FileSystemEventHandler(PatternMatchingEventHandler):
        """File system event handler

        Implement callbacks for file system events.

        :param PatternMatchingEventHandler: Event handler from the watchdog package
        :type PatternMatchingEventHandler: watchdog.events.PatternMatchingEventHandler
        """

        def __init__(self, client, patterns):
            self.client = client
            super().__init__(patterns=patterns)

        def on_created(self, event: watchdog.events.FileSystemEvent) -> None:
            """New file created

            :param event: Filesystem event
            :type event: watchdog.events.FileSystemEvent
            """
            try:
                self.client.on_filesystem_object_created(event.src_path)
            except Exception as e:  # pylint: disable=broad-except
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")

        def on_moved(self, event: watchdog.events.FileSystemEvent) -> None:
            """File moved

            :param event: Filesystem event
            :type event: watchdog.events.FileSystemEvent
            """
            try:
                self.client.on_filesystem_object_created(event.dest_path)
            except Exception as e:  # pylint: disable=broad-except
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")

    def __init__(self, client, path: str, mask: str, recursive=False):
        self.client = client
        self.path = path
        self.mask = mask
        self.recursive = recursive
        self.observer = Observer()
        self.handler = self.FileSystemEventHandler(self.client, patterns=[self.mask])

    def start(self) -> None:
        """Start watching.

        Start `FileSystemEventHandler`
        """
        self.observer.schedule(self.handler, self.path, recursive=self.recursive)
        self.observer.start()
        runtime.logger.info(
            f"Started watching {self.path} for new files matching pattern '{self.mask}'"
        )

    def stop(self) -> None:
        """Stop watching.

        Stop `FileSystemEventHandler`
        """
        self.observer.stop()
        self.observer.join()
        runtime.logger.info("File system watcher stopped")

    def run(self) -> None:
        """Main loop

        Start `FileSystemEventHandler` and do nothing.
        """
        self.start()
        while not self.client.shutdown_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.client.shutdown_event.set()
            except Exception as e:  # pylint: disable=broad-except
                runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")
        self.stop()

    def run_as_daemon(self):
        """Run as daemon"""
        t = Thread(target=self.run)
        t.daemon = True
        t.start()


class FileUploader:
    """Watch for new files matching a specified `mask` in `source` directory, upload to
    Mascope after file has not been accessed for specified timeout period.
    """

    def __init__(self, source_path: str, mask: str):
        self.shutdown_event = Event()
        self.jobs = Queue()
        self.watcher = FileSystemWatcher(
            client=self, path=source_path, mask=mask, recursive=False
        )

    def on_filesystem_object_created(self, fname: str) -> None:
        """Callback on file created.

        First wait while filesize is changing. Then check file access
        by dummy rename operation. Finally, put file into `self.jobs` queue.

        :param fname: File path
        :type fname: str
        """
        runtime.logger.info(f"File created: {fname}")
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
                runtime.logger.info(f"File {fname} is not ready")
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

    def run_until_complete(self):
        """
        Main loop that continuously checks for jobs to process and uploads files if necessary.

        This method runs in a loop until the `shutdown_event` is set. It periodically checks
        for new jobs from the `jobs` queue and processes them. If a job is found, it checks the
        time since the last access and decides whether to requeue the job or upload the file.
        The loop handles several exceptions to ensure smooth operation and logs critical errors.

        Exceptions Handled:
            - Empty: Raised when the `jobs` queue is empty.
            - FileNotFoundError: Raised when the file to be uploaded is not found.
            - SameFileError: Raised when there is an attempt to upload the same file.
            - KeyboardInterrupt: Raised when the process is interrupted by the user.
            - Exception: Catches all other exceptions and logs them as critical errors.

        The method ensures that the `shutdown_event` is set when exiting, either normally or due
        to an exception.
        """
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
                fname = None
                try:
                    fname = self.jobs.get_nowait()
                    runtime.logger.debug(fname)
                    if self.seconds_since_last_access(fname) < runtime.config.timeout:
                        self.jobs.put(fname)
                        runtime.logger.debug(f"Put {fname} back to queue")
                        continue
                    # Spawn a thread for file upload
                    upload_thread = Thread(
                        target=process_file_upload, args=(fname,), daemon=True
                    )
                    upload_thread.start()
                except Empty:
                    continue

        except KeyboardInterrupt:
            runtime.logger.info("Shutdown requested by user.")
        except Exception as e:  # pylint: disable=broad-except
            runtime.logger.error(f"{e.__class__.__name__}({str(e)})")
        finally:
            self.shutdown_event.set()


def run() -> None:
    """Main function of the application

    Start `FileUploader` thread and wait until it finishes
    """
    # Initialize runtime
    initialize()

    global URL  # pylint: disable=global-statement
    global HOST  # pylint: disable=global-statement
    global PORT  # pylint: disable=global-statement

    PORT = runtime.meta.api_port
    HOST = runtime.config.host
    if HOST and PORT:
        URL = f"http://{HOST}:{PORT}"
    elif HOST:
        URL = f"http://{HOST}"
    if not URL:
        runtime.logger.error(
            "Mascope host not defined, please check configuration. Exiting..."
        )
        raise RuntimeError("Mascope host not defined, please check configuration.")

    if not os.path.isdir(runtime.config.source):
        raise RuntimeError(f"Invalid source directory {runtime.config.source}")
    uploader = FileUploader(runtime.config.source, runtime.config.mask)
    uploader.watcher.run_as_daemon()
    uploader.run_until_complete()


if __name__ == "__main__":
    run()
