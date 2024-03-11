# TODO: TwTool must load library before H5Streamer;
# can be fixed later by refactoring H5Streamer dependencies
import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
)
import argparse
from datetime import timedelta
from multiprocessing import Event, Lock, Queue
from queue import Empty
from threading import Thread
from time import sleep

import requests
import socketio

from dotenv import load_dotenv


from hardware.orbitrap.generator import RawStreamer
from hardware.tofwerk.h5_streamer import H5Streamer
from hardware.tofwerk.lib.TwTool import *

from lib.file_func import zarr_sdk
from lib.peak import calculate_tic
from lib.structs import AttrDict
from lib.util import timestamp_from_filename
from service.lib.filesystem_watcher import FSWatcher
from service.lib.util import load_env_yaml


def create_sample_file_db_record(data):
    """Create a sample file database record by a HTTP request

    :param data: Sample file object to create
    :type data: dict
    :raises Exception: HTTP request failed
    """
    filename = data["filename"]
    print(f"Creating sample file record for file: {filename}")
    instrument_name = filename.split("_")[0]
    committed_length = data["committed_length"]
    date = timestamp_from_filename(filename)
    utc_offset = timedelta(seconds=int(data["utc_offset"]))
    mz_calibration = data.get("mz_calibration")
    tic = calculate_tic(filename)

    sample_file_db_record = {
        "filename": filename,
        "instrument": instrument_name,
        "datetime": date.isoformat(),
        "datetime_utc": (date - utc_offset).isoformat(),
        "length": committed_length,
        "range": data["range"],
        "mz_calibration": mz_calibration,
        "tic": tic,
    }

    headers = {"Content-Type": "application/json"}

    url = f"http://{host}:{port}/api/sample_files"

    response = requests.post(url, headers=headers, json=sample_file_db_record)
    if response.status_code != 200:
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
            print("Canceling...")
            streamer.cancel_event.set()
            # Clear queues
            streamer.spec_queue.get()  # data
            if hasattr(streamer, "tps_queue"):
                streamer.tps_queue.get()  # coordinates
                streamer.tps_queue.get()  # data

        data.update({"filename": data["filename"].replace(" ", "_")})
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
            print("Got poison pill")
            # File finished
            print("Finalizing signal dataset")
            zarr_sdk.finalize_signal_dataset({"value": data}, sample_file)
            data.update(
                {
                    "committed_length": sample_file.props["committed_length"],
                    "range": sample_file.props["range"],
                    "mz_calibration": sample_file.props["mz_calibration"],
                    "utc_offset": sample_file.props["utc_offset"],
                }
            )
            filepath = data.pop("source_filepath")
            print("Deleting file from mailbox")
            os.remove(filepath)
            try:
                create_sample_file_db_record(data)
            except Exception as e:
                print(f"Failed to create database record!: {e}")
            try:
                sio.emit(
                    "instrument_conversion_finished",
                    notification_data,
                )
            except Exception as e:
                print(f"Failed to emit notification: {e}")
        elif spec_i < 0:
            # New file
            try:
                sample_file = zarr_sdk.init_signal_dataset({"value": data})
            except Exception as e:
                print(
                    f"Error starting {data['filename']}: {e.__class__.__name__}({str(e)})"
                )
                cleanup()
                return False
            sample_file = AttrDict(sample_file)
            cache[filename] = sample_file
            try:
                sio.emit("instrument_conversion_started", notification_data)
            except Exception as e:
                print(f"Failed to emit notification: {e}")
        else:
            # New data to existing file
            zarr_sdk.update_signal_dataset({"value": data}, sample_file)
            try:
                print(notification_data["progress"])
                sio.emit("instrument_conversion_progress", notification_data)
            except Exception as e:
                print(f"Failed to emit notification: {e}")
        return True

    def handle_tps_data(data):
        """Handle one point of TPS data from the streamer

        :param data: TPS data object
        :type data: dict
        """
        data.update({"filename": data["filename"].replace(" ", "_")})
        filename = data["filename"]
        spec_i = data["i"]
        sample_file = cache.get(filename)
        if sample_file is None:
            return
        if spec_i is None:
            # File finished
            pass
        elif spec_i < 0:
            # New file
            try:
                zarr_sdk.init_tps_dataset({"value": data}, sample_file)
            except FileExistsError:
                return
        else:
            # New data to existing file
            zarr_sdk.update_tps_dataset({"value": data}, sample_file)

    # Main loop
    while not streamer.shutdown_event.is_set():
        try:
            # Check the queue for new data
            spec_data = streamer.spec_queue.get_nowait()
            spec_i = spec_data["i"]
            # Handle spectrum data
            success = handle_spec_data(spec_data)
            if success and hasattr(streamer, "tps_queue"):
                # If "tps_queue" exists (H5Streamer), handle tps data
                tps_data = streamer.tps_queue.get()
                handle_tps_data(tps_data)
            if spec_i is None:
                # Received poison pill, clear file from cache
                cache.pop(spec_data["filename"])
        except Empty:
            # No data available, wait before retry
            sleep(0.1)


def parse_cmd_args():
    """
    Parse command line arguments
    ------------------------------
    Return dict
    Default argument values: see default_args.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c", "--config", help="path to yaml config file", type=str, required=False
    )
    parser.add_argument(
        "-m",
        "--host",
        help="mascope url (default: localhost)",
        type=str,
        required=False,
    )
    parser.add_argument(
        "-p",
        "--port",
        help="mascope-api service port (default: $MASCOPE_PUBLIC_API_PORT)",
        type=str,
        required=False,
    )
    parser.add_argument(
        "-nj", "--n_jobs", help="number of job processors", type=int, required=False
    )
    parser.add_argument(
        "-s",
        "--source_dir",
        help="source directory for streaming (before date dirs)",
        type=str,
        required=False,
    )

    def streamer_type(st):
        streamer_types = ["H5", "Raw"]
        if st not in streamer_types:
            raise argparse.ArgumentTypeError(
                f"{st}; should be one of the {streamer_types}"
            )
        return st

    parser.add_argument(
        "-st",
        "--streamer_type",
        help="streamer type (H5/Raw)",
        type=streamer_type,
        required=False,
    )
    parser.add_argument(
        "-r", "--recursive", help="recursive", action="store_true", default=False
    )
    parser.add_argument(
        "--ping",
        help="ping source directory for new samples (alt to filesystem event)",
        action="store_true",
        default=False,
    )

    all_args = parser.parse_args()
    cmdline_args = {}
    for arg in vars(all_args):
        if vars(all_args)[arg] is None:
            continue
        cmdline_args[arg] = vars(all_args)[arg]
    file_args = {}
    if all_args.config:
        # service config may be defined in yaml file
        file_args = load_env_yaml(all_args.config)
    return {**file_args, **cmdline_args}


def main():
    """Main loop of the service. Connect socket.io and then do nothing."""
    global sio
    url = f"http://{host}:{port}"
    print(f"Connecting to {url}...")
    while not shutdown_event.is_set():
        # Keep trying to connect to socket.io server
        try:
            sio.connect(url)
            break
        except:
            # Connection timed out, wait before retry
            sleep(1)
    # socket.io connection established
    while not shutdown_event.is_set():
        # Wait for shutdown event
        sleep(1)


load_dotenv()
#
host = None
port = None
cache = None
file_queue = Queue()
shutdown_event = Event()
sio = socketio.Client(logger=True, ssl_verify=False)


def run():
    """Run the service

    :raises Exception: Parsing command line arguments failed
    """
    global host
    global port
    global cache
    global file_queue
    global shutdown_event

    # Parse command line arguments
    args = parse_cmd_args()
    print(args)

    host = args.get("host", "127.0.0.1")
    port = args.get("port", os.environ.get("MASCOPE_PUBLIC_API_PORT"))

    # Validate streamer type
    streamer_type = args["streamer_type"]
    if streamer_type == "H5":
        streamer_class = H5Streamer
        file_mask = "*.h5"
    elif streamer_type == "Raw":
        streamer_class = RawStreamer
        file_mask = "*.raw"
    else:
        raise Exception(f"Unknown streamer type: {streamer_type}")

    # Initialize streamer thread(s)
    n_jobs = args.get("n_jobs", 1)
    cache = dict()
    streamer_lock = Lock()
    streamers = [
        streamer_class(
            file_queue=file_queue,
            shutdown_event=shutdown_event,
            lock=streamer_lock,
        )
        for _ in range(n_jobs)
    ]
    # Start streamer thread(s)
    for streamer in streamers:
        streamer.start()
        streamer_processor = Thread(target=process_stream, args=(streamer,))
        streamer_processor.start()

    source_path = args.get("source_dir", ".")

    if not os.path.exists(source_path):
        print(f"Creating missing source directory {source_path}")
        os.makedirs(source_path)

    # Initialize file system watcher
    fs_watcher = FSWatcher(
        path=source_path,
        mask=file_mask,
        file_queue=file_queue,
        recursive=args["recursive"],  # default False
        ping=args["ping"],  # default False
        shutdown_event=shutdown_event,
    )
    # Start file system watcher
    fs_watcher.run_as_daemon()

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
