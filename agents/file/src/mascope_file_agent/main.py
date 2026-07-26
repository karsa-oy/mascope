import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Event, Queue
from queue import Empty
from threading import Thread

import watchdog
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

import mascope_sdk
from mascope_file_agent import __version__
from mascope_file_agent import config as agent_config
from mascope_file_agent.config import ConfigError
from mascope_file_agent.wizard import run_setup_wizard
from mascope_runtime import Runtime


mascope_sdk.SERVICE_NAME = "file-agent"
from mascope_sdk import api_post_file  # noqa: E402  (needs SERVICE_NAME set first)
from mascope_sdk.exceptions import (  # noqa: E402
    AuthenticationError,
    NotFoundError,
    ValidationError,
)


# TODO: Use TUS protocol for large file uploads, see issue #1131
# https://github.com/karsa-oy/mascope/issues/1131
FILE_UPLOAD_SIZE_LIMIT = 100 * 1024**2  # 100 MB
HOST = None
PORT = None
URL = None
SHUTDOWN_EVENT = Event()

runtime = None

executor = ThreadPoolExecutor(max_workers=3)


def get_upload_filename(filepath: str) -> str | None:
    """Compute the upload filename by applying configured prefix and/or suffix.

    Returns the modified filename if prefix or suffix is configured,
    otherwise returns None (indicating the original filename should be used).

    :param filepath: Full path to the file
    :type filepath: str
    :return: Modified filename or None
    :rtype: str | None
    """
    prefix = runtime.config.filename_prefix or ""
    suffix = runtime.config.filename_suffix or ""
    if not prefix and not suffix:
        return None
    for label, value in (("filename_prefix", prefix), ("filename_suffix", suffix)):
        if any(sep in value for sep in ("/", "\\", os.sep) if sep) or ".." in value:
            raise ValueError(f"{label} contains invalid characters: {value!r}")
    basename = os.path.basename(filepath)
    stem, ext = os.path.splitext(basename)
    return f"{prefix}{stem}{suffix}{ext}"


def process_file_upload(filepath: str, max_retries: int = 10) -> None:
    """Process file upload

    :param filepath: Full path to the file to be uploaded
    :type filepath: str
    """
    for attempt in range(1, max_retries + 1):
        try:
            upload_sample_file(filepath)
            return
        except ValueError as ve:
            runtime.logger.error(f"File upload failed: {ve}")
            break  # do not retry on validation errors
        except AuthenticationError as e:
            runtime.logger.error(
                f"File upload failed for file {os.path.basename(filepath)}: {e} "
                "Retrying will not help - fix the access_token in the "
                "file-agent configuration and restart the agent."
            )
            break  # a rejected token stays rejected; do not retry
        except (NotFoundError, ValidationError) as e:
            runtime.logger.error(
                f"File upload failed for file {os.path.basename(filepath)}: {e} "
                "Retrying will not help - the server rejected the request. "
                "A 404 usually means the configured host is not the Mascope "
                "API (in development setups the frontend dev server cannot "
                "receive uploads; use the backend address, e.g. "
                "http://localhost:8090). Fix 'host' in the file-agent "
                "configuration and restart the agent."
            )
            break  # a wrong address or rejected payload cannot heal by waiting
        except Exception as e:
            # Timeouts, connection and server errors are transient - retry.
            # The message carries the specific cause (e.g. connection refused,
            # HTTP status + server error message).
            # INFO per attempt: retries are routine on a flaky network; the
            # final give-up below logs at ERROR
            runtime.logger.info(
                f"Upload attempt {attempt}/{max_retries} for file "
                f"{os.path.basename(filepath)} failed: {e}"
            )
            runtime.logger.info("Retrying upload in 30 seconds...")
            time.sleep(30)
    # Max retries exceeded, give up
    runtime.logger.error(
        f"File upload failed for file {os.path.basename(filepath)} after {attempt} attempts"
    )
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
            f"File size ({round(file_size / (1024**2), 1)} MB) exceeds the maximum "
            f"allowed size ({FILE_UPLOAD_SIZE_LIMIT / (1024**2)} MB)"
        )

    # Make file upload request
    runtime.logger.debug(f"Making an upload request to {URL} for file {filepath}")
    upload_filename = get_upload_filename(filepath)
    if upload_filename:
        runtime.logger.info(
            f"Uploading file {os.path.basename(filepath)} as {upload_filename}"
        )
    # Raises a typed mascope_sdk exception carrying the specific cause
    # (rejected token, timeout, connection error, server error message).
    api_post_file(
        url=URL,
        path="sample/files/upload",
        access_token=runtime.config.access_token,
        filepath=filepath,
        upload_filename=upload_filename,
    )

    runtime.logger.info(f"File upload of file {os.path.basename(filepath)} succeeded!")


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


def resolve_settings(mascope_path: str, env_path: str) -> dict:
    """Load the agent settings, running the guided setup when needed.

    Settings come from the single user-facing ``config.toml`` at the root
    of `mascope_path`. When it is missing, settings from a pre-config.toml
    install are migrated; when required settings are still missing (or the
    agent was started with ``--setup``), the interactive wizard collects
    them and writes the file.

    :param mascope_path: The agent's data directory (MASCOPE_PATH)
    :type mascope_path: str
    :param env_path: Path of the ``.runtime/env/prod`` directory
    :type env_path: str
    :return: Complete, validated settings dict
    :rtype: dict
    :raises ConfigError: When settings are missing and the wizard cannot run,
        or the watched folder does not exist
    """
    config_path = os.path.join(mascope_path, agent_config.CONFIG_FILENAME)
    if os.path.exists(config_path):
        settings = agent_config.load_user_config(config_path)
    else:
        settings = agent_config.load_legacy_config(env_path)
        if settings:
            agent_config.write_user_config(config_path, settings)
            print(f"Migrated existing settings to {config_path}")
        else:
            settings = agent_config.merge_settings({})

    if "--setup" in sys.argv[1:] or agent_config.missing_settings(settings):
        if not (sys.stdin and sys.stdin.isatty()):
            raise ConfigError(
                "The agent is not configured. Start it in a console to use "
                "the guided setup, or fill in host, access_token and source "
                f"in:\n  {config_path}"
            )
        settings = run_setup_wizard(settings)
        agent_config.write_user_config(config_path, settings)
        print(f"Settings saved to {config_path}\n")

    if not os.path.isdir(settings["source"]):
        raise ConfigError(
            f"The watched folder does not exist: {settings['source']}\n"
            f"Update 'source' in {config_path}, or restart the agent "
            "with --setup to run the guided setup again."
        )
    return settings


def initialize() -> None:
    """Initialize the application and runtime depending on dev/prod mode

    If in prod mode, check if runtime directory structure exists, and create if not.

    :return: Return nothing
    :rtype: None
    """
    global runtime
    # check if we are running in a pyinstaller bundle
    bundled = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    if bundled:
        # prod mode
        # set MASCOPE_PATH as %AppData%\Mascope\FileAgent
        mascope_path = mkdir(os.environ["APPDATA"], "Mascope", "FileAgent")
        os.environ.setdefault("MASCOPE_PATH", mascope_path)
        # setup runtime environment
        env_path = mkdir(mascope_path, ".runtime", "env", "prod")
        mkdir(mascope_path, "logs")
        # resolve user settings (guided setup on first run) and regenerate
        # the runtime-format config the mascope_runtime loader reads
        settings = resolve_settings(mascope_path, env_path)
        agent_config.write_runtime_config(env_path, settings, mascope_path)
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
            except Exception:
                runtime.logger.exception("Unexpected error handling filesystem event")

        def on_moved(self, event: watchdog.events.FileSystemEvent) -> None:
            """File moved

            :param event: Filesystem event
            :type event: watchdog.events.FileSystemEvent
            """
            try:
                self.client.on_filesystem_object_created(event.dest_path)
            except Exception:
                runtime.logger.exception("Unexpected error handling filesystem event")

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
            except Exception:
                runtime.logger.exception("Unexpected error in the watcher loop")
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
                runtime.logger.debug(f"File {fname} is not ready")
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
                    # Submit file upload task for the thread pool executor
                    executor.submit(process_file_upload, fname)
                except Empty:
                    continue

        except KeyboardInterrupt:
            runtime.logger.info("Shutdown requested by user.")
        except Exception:
            runtime.logger.exception("Unexpected error in the upload loop")
        finally:
            self.shutdown_event.set()


def pause_before_exit() -> None:
    """Keep the console window open so double-click users can read the error."""
    if getattr(sys, "frozen", False) and sys.stdin and sys.stdin.isatty():
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass


def run() -> None:
    """Main function of the application

    Start `FileUploader` thread and wait until it finishes
    """
    # Initialize runtime
    try:
        initialize()
    except ConfigError as e:
        print(f"\nConfiguration error:\n{e}\n")
        if runtime is not None:
            # Also record it in the agent log: without this a misconfigured
            # prod agent (started headless) dies invisibly
            runtime.logger.error(f"Configuration error: {e}")
        pause_before_exit()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(1)

    runtime.logger.info(f"Mascope File Agent {__version__}")

    global URL
    global HOST
    global PORT

    PORT = runtime.meta.api_port
    HOST = runtime.config.host
    match runtime.mode:
        case "dev":
            URL = f"http://{HOST}:{PORT}"
        case "prod":
            # https unless the host is configured with an explicit scheme
            URL = agent_config.base_url(HOST) if HOST else None
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
    executor.shutdown(wait=True)


if __name__ == "__main__":
    run()
