import os

from datetime import timedelta, datetime
from multiprocessing import Event, Lock, Queue
from queue import Empty
from threading import Thread
from time import sleep

import requests
import socketio

import mascope_lib.runtime as lib_runtime

lib_runtime.init()

from mascope_lib.file_func import zarr_sdk, get_instrument_type

from mascope_lib.structs import AttrDict
from mascope_lib.util import timestamp_from_filename

import mascope_hardware.runtime as hardware_runtime

hardware_runtime.init()

# the order of the next two import matters; if the order is
# reversed, we get a mysterious error:
#        ValueError: Index 'mz' must be monotonically increasing
from mascope_hardware.tofwerk.h5_streamer import H5Streamer  # this comes first
from mascope_hardware.orbitrap.generator import RawStreamer  # and this comes second


from mascope_runtime import MascopeRuntimeModule

from .watcher import FSWatcher


runtime = MascopeRuntimeModule("file-converter")


host = runtime.config.server if runtime.mode == "prod" else "localhost"
url = f"http://{host}:{runtime.meta.api_port}"


def create_sample_file_db_record(data):
    """Create a sample file database record by a HTTP request

    :param data: Sample file object to create
    :type data: dict
    :raises Exception: HTTP request failed
    """
    filename = data["filename"]
    instrument_type = get_instrument_type(filename)
    runtime.logger.info(f"Creating sample file record for file: {filename}")
    instrument_name = filename.split("_")[0]
    committed_length = data["committed_length"]
    utc_offset = timedelta(seconds=int(data["utc_offset"]))
    mz_calibration = data.get("mz_calibration")
    polarity = data.get("polarity")
    method_file = data.get("method_file")
    tic = data.get("tic")

    if instrument_type == "tof":
        date = timestamp_from_filename(filename).isoformat()
    else:
        date = data.get("timestamp")

    date_utc = (datetime.fromisoformat(date) - utc_offset).isoformat()

    sample_file_db_record = {
        "filename": filename,
        "instrument": instrument_name,
        "datetime": date,
        "datetime_utc": date_utc,
        "length": committed_length,
        "range": data["range"],
        "mz_calibration": mz_calibration,
        "tic": tic,
        "polarity": polarity,
    }
    if method_file:
        sample_file_db_record["method_file"] = method_file

    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{url}/api/sample/files", headers=headers, json=sample_file_db_record
    )
    if response.status_code != 201:
        raise Exception(
            f"Failed to create database record! Status code: {response.status_code}"
        )


def process_stream(streamer):
    """Process data stream from the streamer thread

    :param streamer: Data streamer instance
    :type streamer: H5Streamer or RawStreamer
    """
    global cache
    global sio

    # Handlers
    def handle_spec_data(data):
        """Process one spectrum from the streamer

        :param data: Data object
        :type data: dict
        """

        def cleanup():
            """Clean-up routine on stream canceled"""
            runtime.logger.info("Canceling...")
            streamer.cancel_event.set()
            # Clear queues
            streamer.spec_queue.get()  # data
            if hasattr(streamer, "tps_queue"):
                streamer.tps_queue.get()  # coordinates
                streamer.tps_queue.get()  # data

        filename = data["filename"]
        instrument_name = filename.split("_")[0]
        spec_i = data["i"]
        sample_file = cache.get(filename)
        notification_data = {
            "filename": filename,
            "instrument": instrument_name,
            "progress": streamer.progress,
        }
        if spec_i is None:
            runtime.logger.info("Signal termination detected, finalizing dataset")
            zarr_sdk.finalize_signal_dataset(data, sample_file)
            data.update(
                {
                    "committed_length": sample_file.props["committed_length"],
                    "range": sample_file.props["range"],
                    "mz_calibration": sample_file.props["mz_calibration"],
                    "utc_offset": sample_file.props["utc_offset"],
                    "polarity": sample_file.props["polarity"],
                    "method_file": sample_file.props["method_file"],
                    "tic": sample_file.props["tic"],
                }
            )
            filepath = data.pop("source_filepath")
            runtime.logger.info("Deleting file from streams folder")
            try:
                os.remove(filepath)
            except FileNotFoundError as e:
                runtime.logger.error(
                    f"Failed to delete file {filepath} from the streams folder"
                )
                runtime.logger.exception(e)

            # Send request to Mascope backend to create sample file record in the db
            try:
                create_sample_file_db_record(data)
            except Exception as e:
                runtime.logger.error(f"Failed to create database record")
                runtime.logger.exception(e)
            try:
                sio.emit(
                    "instrument_conversion_finished",
                    notification_data,
                )
            except Exception as e:
                runtime.logger.error(f"Failed to emit notification")
                runtime.logger.exception(e)
        elif spec_i < 0:
            # New file
            try:
                sample_file = zarr_sdk.init_signal_dataset(data)
            except Exception as e:
                runtime.logger.error(f"Failed to start {data['filename']}")
                runtime.logger.exception(e)
                cleanup()
                return False
            sample_file = AttrDict(sample_file)
            cache[filename] = sample_file
            try:
                sio.emit("instrument_conversion_started", notification_data)
            except Exception as e:
                runtime.logger.error(f"Failed to emit notification")
                runtime.logger.exception(e)
        else:
            # New data to existing file
            zarr_sdk.update_signal_dataset(data, sample_file)
            try:
                runtime.logger.info(notification_data["progress"])
                sio.emit("instrument_conversion_progress", notification_data)
            except Exception as e:
                runtime.logger.error(f"Failed to emit notification")
                runtime.logger.exception(e)
        return True

    def format_filename(generator_data: dict) -> str:
        """Format raw filename (from data acquisition software) into Mascope sample file name

        - Replace white space with underscore
        - Append filename with polarity character (+/-)

        :param generator_data: Data object from the generator thread, must contain "filename" key
        :type generator_data: dict
        :return: Formatted filename
        :rtype: str
        """
        formatted_filename = generator_data["filename"].replace(" ", "_")
        formatted_filename = "_".join([formatted_filename, generator_data["polarity"]])
        return formatted_filename

    # Main loop
    while not streamer.shutdown_event.is_set():
        try:
            # Check the queue for new data
            spec_data = streamer.spec_queue.get_nowait()
            # Format filename
            spec_data.update({"filename": format_filename(spec_data)})
            spec_i = spec_data["i"]
            # Handle spectrum data
            success = handle_spec_data(spec_data)
            if success and hasattr(streamer, "tps_queue"):
                # If "tps_queue" exists (H5Streamer), handle tps data
                tps_data = streamer.tps_queue.get()
                # Format filename
                tps_data.update({"filename": format_filename(tps_data)})
                handle_tps_data(tps_data)
            if spec_i is None:
                # Received poison pill, clear file from cache
                cache.pop(spec_data["filename"])
        except Empty:
            # No data available, wait before retry
            sleep(0.1)


def main():
    """Main loop of the service. Connect socket.io and then do nothing."""
    global sio
    runtime.logger.info(f"Attempting to connect to {url}...")
    while not shutdown_event.is_set():
        # Keep trying to connect to socket.io server
        try:
            sio.connect(url)
            break
        except:
            # Connection timed out, wait before retry
            sleep(1)
    runtime.logger.info(f"Connection established to {url}")
    # socket.io connection established
    while not shutdown_event.is_set():
        # Wait for shutdown event
        sleep(1)


cache = None
raw_file_queue = Queue()
h5_file_queue = Queue()
shutdown_event = Event()

sio = socketio.Client(logger=False, ssl_verify=False)


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
        H5Streamer(
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

    # orbi streamers
    raw_streamers = [
        RawStreamer(
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

    streamers = [*raw_streamers, *h5_streamers]

    # Start streamer thread(s)
    for streamer in streamers:
        streamer.start()
        streamer_processor = Thread(target=process_stream, args=(streamer,))
        streamer_processor.start()

    try:
        # Run main loop
        main()
    except KeyboardInterrupt:
        # Shutdown gracefully on ctrl+C
        shutdown_event.set()
    except:
        # Shutdown gracefully on exception
        shutdown_event.set()
    streamer_processor.join()


if __name__ == "__main__":
    # Run the service
    run()
