import os

from multiprocessing import Event, Lock, Queue
from time import sleep

from mascope_backend.file_converter.socket.client import FileConverterSocketClient
from mascope_backend.file_converter.watcher import FSWatcher

from mascope_thermo.generator import RawProcessor
from mascope_tofwerk.generator import H5Processor

from .runtime import runtime

host = runtime.config.server if runtime.mode == "prod" else "localhost"
url = f"http://{host}:{runtime.meta.api_port}"


def main():
    """Main loop of the service. Connect socket.io and then do nothing."""

    global socket_client
    runtime.logger.info(f"Attempting to connect to {url}...")
    while not shutdown_event.is_set():
        # Keep trying to connect to socket.io server
        try:
            socket_client.connect()
            break
        except Exception:
            # Connection timed out, wait before retry
            sleep(1)
    # socket.io connection established
    while not shutdown_event.is_set():
        # Wait for shutdown event
        sleep(1)


# Global variables
cache = None
raw_file_queue = Queue()
h5_file_queue = Queue()
shutdown_event = Event()
socket_client = FileConverterSocketClient(url)


def run():
    """Run the service

    :raises Exception: Parsing command line arguments failed
    """

    global cache
    global raw_file_queue
    global h5_file_queue
    global shutdown_event

    if not os.path.exists(runtime.config.source):
        runtime.logger.info(
            f"Creating missing source directory {runtime.config.source}"
        )
        os.makedirs(runtime.config.source)

    # Initialize streamer thread(s)
    cache = dict()
    streamer_lock = Lock()

    # tof streamers
    h5_streamers = [
        H5Processor(
            socket_client=socket_client,
            file_queue=h5_file_queue,
            shutdown_event=shutdown_event,
            lock=streamer_lock,
        )
        for _ in range(runtime.config.h5_threads)
    ]
    h5_fs_watcher = FSWatcher(
        path=runtime.config.source,
        pattern="*.h5",
        file_queue=h5_file_queue,
        interval=runtime.config.interval,  # default 3
        shutdown_event=shutdown_event,
    )
    h5_fs_watcher.start()

    # orbi file processors
    raw_processors = [
        RawProcessor(
            socket_client=socket_client,
            file_queue=raw_file_queue,
            shutdown_event=shutdown_event,
            lock=streamer_lock,
        )
        for _ in range(runtime.config.raw_threads)
    ]
    raw_fs_watcher = FSWatcher(
        path=runtime.config.source,
        pattern="*.raw",
        file_queue=raw_file_queue,
        interval=runtime.config.interval,  # default 3
        shutdown_event=shutdown_event,
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
        shutdown_event.set()


if __name__ == "__main__":
    # Run the service
    run()
