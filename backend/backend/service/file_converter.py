# TODO: TwTool must load library before H5Streamer;
# can be fixed later by refactoring H5Streamer dependencies
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
from hardware.tofwerk.lib.TwTool import *

import argparse
import asyncio
import socketio
from datetime import timedelta
from dotenv import load_dotenv
from multiprocessing import Event, Queue, Lock
from queue import Empty

from backend.lib.file import zarr_sdk
from backend.lib.struct import AttrDict, LRUDict
from backend.lib.util import timestamp_from_filename
from hardware.tofwerk.h5_streamer import H5Streamer
from hardware.orbitrap.generator import RawStreamer
from backend.service.lib.filesystem_watcher import FSWatcher
from backend.service.lib.util import load_env_yaml


async def create_sample_file_db_record(data):
    filename = data['filename']
    instrument_name = filename.split('_')[0]
    committed_length = data['committed_length']
    date = timestamp_from_filename(filename)
    utc_offset = timedelta(seconds=int(data['utc_offset']))
    mz_calibration = data.get('mz_calibration')
    tic = cache.get(filename)['signal'].sum(dim='time').sum(dim='mz').compute().item()
    await sio.emit(
            'sample_file_create',
            [{
                "filename": filename,
                "instrument": instrument_name,
                "datetime": date.isoformat(),
                "datetime_utc": (date - utc_offset).isoformat(),
                "length": committed_length,
                "range": data['range'],
                "mz_calibration": mz_calibration,
                "tic": tic,
            }]
        )


async def streamer_processor(streamer):
    global cache
    global sio
    # Handlers
    async def handle_spec_data(data):
        def cleanup():
            print("Canceling...")
            streamer.cancel_event.set()
            # Clear queues
            streamer.spec_queue.get() # data
            if hasattr(streamer, 'tps_queue'):
                streamer.tps_queue.get() # coordinates
                streamer.tps_queue.get() # data

        filename = data['filename']
        instrument_name = filename.split('_')[0]
        spec_i = data['i']
        cache_item = cache.get(filename)
        notification_data = {
            'filename': filename,
            'instrument': instrument_name,
            'progress': streamer.progress,
        }
        if spec_i is None:
            # File finished
            zarr_sdk.finalize_signal_dataset({'value': data}, cache_item)
            data.update({
                'committed_length': cache_item.props['committed_length'],
                'range': cache_item.props['range'],
                'mz_calibration': cache_item.props['mz_calibration'],
                'utc_offset': cache_item.props['utc_offset']
                })
            filepath = data.pop('source_filepath')
            os.remove(filepath)
            try:
                await create_sample_file_db_record(data)
            except socketio.exceptions.BadNamespaceError:
                print("Failed to create database record! No connection to server.")
            if sio.connected:
                await sio.emit(
                    'instrument_conversion_finished',
                    notification_data,
                )
        elif spec_i < 0:
            # New file
            try:
                cache_item = zarr_sdk.init_signal_dataset({'value': data})
            except Exception as e:
                print(f"Error starting {data['filename']}: {e.__class__.__name__}({str(e)})")
                cleanup()
                return False
            cache_item = AttrDict(cache_item)
            cache[filename] = cache_item
            if sio.connected:
                await sio.emit(
                    'instrument_conversion_started',
                    notification_data,
                )
        else:
            # New data to existing file
            zarr_sdk.update_signal_dataset({'value': data}, cache_item)
            if sio.connected:
                await sio.emit(
                    'instrument_conversion_progress',
                    notification_data,
                )
        return True
            
    async def handle_tps_data(data):
        filename = data['filename']
        spec_i = data['i']
        cache_item = cache.get(filename)
        if cache_item is None:
            return
        if spec_i is None:
            # File finished
            pass
        elif spec_i < 0:
            # New file
            try:
                zarr_sdk.init_tps_dataset({'value': data}, cache_item)
            except FileExistsError:
                return
        else:
            # New data to existing file
            zarr_sdk.update_tps_dataset({'value': data}, cache_item)

    # Main loop
    while not streamer.shutdown_event.is_set():
        try:
            spec_data = streamer.spec_queue.get_nowait()
            success = await handle_spec_data(spec_data)
            if success and hasattr(streamer, 'tps_queue'):
                tps_data = streamer.tps_queue.get()
                await handle_tps_data(tps_data)
        except Empty:
            await asyncio.sleep(.1)


def parse_cmd_args():
    """
    Parse command line arguments
    ------------------------------
    Return dict
    Default argument values: see default_args.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c", "--config",
        help="path to yaml config file",
        type=str, required=False
    )
    parser.add_argument(
        "-m", "--host",
        help="mascope url (default: localhost)",
        type=str, required=False
    )
    parser.add_argument(
        "-p", "--port",
        help="mascope-api service port (default: $MASCOPE_PUBLIC_API_PORT)",
        type=str, required=False
    )
    parser.add_argument(
        "-nj", "--n_jobs",
        help="number of job processors",
        type=int, required=False
    )
    parser.add_argument(
        "-s", "--source_dir",
        help="source directory for streaming (before date dirs)",
        type=str, required=False
    )
    def streamer_type(st):
        streamer_types = ['H5', 'Raw']
        if st not in streamer_types:
            raise argparse.ArgumentTypeError(f"{st}; should be one of the {streamer_types}")
        return st
    parser.add_argument(
        "-st", "--streamer_type",
        help="streamer type (H5/Raw)",
        type=streamer_type, required=False
    )
    parser.add_argument(
        "-r", "--recursive",
        help="recursive",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--ping",
        help="ping source directory for new samples (alt to filesystem event)",
        action='store_true',
        default=False
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
    return {
        **file_args,
        **cmdline_args
        }

async def main():
    global sio
    url = f"http://{host}:{port}"
    print(f"Connecting to {url}...")
    while not shutdown_event.is_set():
        try:
            await sio.connect(url)
            break
        except:
            await asyncio.sleep(1)
    while not shutdown_event.is_set():
        await asyncio.sleep(1)



load_dotenv()

host = None
port = None
cache = None
file_queue = Queue()
shutdown_event = Event()
sio = socketio.AsyncClient(logger=True, ssl_verify=False)


def run():
    global host
    global port
    global cache
    global file_queue
    global shutdown_event

    args = parse_cmd_args()
    print(args)

    host = args.get('host', '127.0.0.1')
    port = args.get('port', os.environ.get('MASCOPE_PUBLIC_API_PORT'))

    streamer_type = args['streamer_type']
    if streamer_type == 'H5':
        streamer_class = H5Streamer
        file_mask = '*.h5'
    elif streamer_type == 'Raw':
        streamer_class = RawStreamer
        file_mask = '*.raw'
    else:
        raise Exception(f"Unknown streamer type: {streamer_type}")

    n_jobs = args.get('n_jobs', 1)
    cache = LRUDict(n_jobs)
    streamer_lock = Lock()
    streamers = [
        streamer_class(
            file_queue=file_queue,
            shutdown_event=shutdown_event,
            lock=streamer_lock,
        )
        for _ in range(n_jobs)
    ]
    loop = asyncio.get_event_loop()
    for streamer in streamers:
        streamer.start()
        loop.create_task(streamer_processor(streamer))

    source_path = args.get('source_dir', '.')
    ping = args['ping']

    if not os.path.exists(source_path):
        print(f"Creating missing source directory {source_path}")
        os.makedirs(source_path)

    fs_watcher = FSWatcher(
        path=source_path,
        mask=file_mask,
        file_queue=file_queue,
        recursive=False,
        ping=ping,
        shutdown_event=shutdown_event,
        )
    fs_watcher.run_as_daemon()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        shutdown_event.set()
    except:
        shutdown_event.set()


if __name__ == '__main__':
    run()