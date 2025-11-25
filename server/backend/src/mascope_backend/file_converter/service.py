import os

from multiprocessing import Queue
from threading import Event
from time import sleep

from mascope_backend.file_converter.socket.client import FileConverterSocketClient
from mascope_backend.file_converter.watcher import FSWatcher

from mascope_thermo.processor import RawProcessor
from mascope_tofwerk.processor import H5Processor

from .runtime import runtime


def main():
    """Main loop of the service. Connect socket.io and then do nothing."""
    runtime.logger.info(f"Attempting to connect to {URL}...")
    while not SHUTDOWN_EVENT.is_set():
        # Keep trying to connect to socket.io server
        try:
            SOCKET_CLIENT.connect()
            break
        except Exception:
            # Connection timed out, wait before retry
            sleep(1)
    # socket.io connection established
    while not SHUTDOWN_EVENT.is_set():
        # Wait for shutdown event
        sleep(1)


# Global variables
SHUTDOWN_EVENT = Event()
HOST = runtime.config.server if runtime.mode == "prod" else "localhost"
URL = f"http://{HOST}:{runtime.meta.api_port}"
SOCKET_CLIENT = FileConverterSocketClient(URL)


def run():
    """Run the service

    :raises Exception: Parsing command line arguments failed
    """

    if not os.path.exists(runtime.config.source):
        runtime.logger.info(
            f"Creating missing source directory {runtime.config.source}"
        )
        os.makedirs(runtime.config.source)

    # Initialize streamer thread(s)
    # tof streamers
    h5_file_queue = Queue()
    h5_streamers = [
        H5Processor(
            socket_client=SOCKET_CLIENT,
            file_queue=h5_file_queue,
            shutdown_event=SHUTDOWN_EVENT,
        )
        for _ in range(runtime.config.h5_threads)
    ]
    h5_fs_watcher = FSWatcher(
        path=runtime.config.source,
        pattern="*.h5",
        file_queue=h5_file_queue,
        interval=runtime.config.interval,  # default 3
        shutdown_event=SHUTDOWN_EVENT,
    )
    h5_fs_watcher.start()

    # orbi file processors
    raw_file_queue = Queue()
    raw_processors = [
        RawProcessor(
            socket_client=SOCKET_CLIENT,
            file_queue=raw_file_queue,
            shutdown_event=SHUTDOWN_EVENT,
        )
        for _ in range(runtime.config.raw_threads)
    ]
    raw_fs_watcher = FSWatcher(
        path=runtime.config.source,
        pattern="*.raw",
        file_queue=raw_file_queue,
        interval=runtime.config.interval,  # default 3
        shutdown_event=SHUTDOWN_EVENT,
    )
    raw_fs_watcher.start()

    processors = [*raw_processors, *h5_streamers]

    # Start processor thread(s)
    for processor in processors:
        processor.start()

    try:
        # Run main loop
        main()
    except Exception:
        # Shutdown gracefully on exception
        SHUTDOWN_EVENT.set()
    finally:
        # Wait for all threads to finish
        for processor in processors:
            processor.join()
        raw_fs_watcher.join()
        h5_fs_watcher.join()


if __name__ == "__main__":
    # Run the service
    run()
