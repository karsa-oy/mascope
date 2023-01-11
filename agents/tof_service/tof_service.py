import argparse
import asyncio
import os
import shutil
import socketio
from multiprocessing import Event
from queue import Empty

from hardware.tofwerk.tof_streamer import TofDaqStreamer
from lib.util import load_env_yaml


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
        help="Mascope host IP",
        type=str, required=False
    )
    parser.add_argument(
        "-p", "--port",
        help="Mascope socket.io port",
        type=str, required=False
    )
    parser.add_argument(
        "-t", "--target",
        help="target directory",
        type=str, required=False
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


async def streamer_processor(streamer):
    global sio
    # Handlers
    async def handle_spec_data(data):
        filename = data['filename']
        instrument_name = filename.split('_')[0]
        spec_i = data['i']
        notification_data = {
            'filename': filename,
            'instrument': instrument_name,
            'progress': streamer.progress,
        }
        if spec_i is None:
            # File finished
            print("File finished")
            raw_filename = data['source_filepath']
            global target_path
            if not os.path.exists(target_path):
                print("Creating mailbox: %s" %target_path)
                os.mkdir(target_path)
            while True:
                try:
                    shutil.copyfile(
                        raw_filename,
                        os.path.join(target_path, os.path.basename(raw_filename))
                        )
                    break
                except Exception as e:
                    print("Failed to copy acquired file: %s" %e)
                    await sio.sleep(1)
            if sio.connected:
                await sio.emit(
                    'instrument_acquisition_finished',
                    notification_data,
                )
        elif spec_i < 0:
            # New file
            print("New file: %s" %filename)
            if sio.connected:
                await sio.emit(
                    'instrument_acquisition_started',
                    notification_data,
                )
        else:
            # New data to existing file
            if sio.connected:
                await sio.emit(
                    'instrument_acquisition_progress',
                    notification_data,
                )
        print("%.2f" %streamer.progress)
        return True

    async def handle_tps_data(data):
        return

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


async def main():
    global host
    global port
    global sio

    url = None
    if host and port:
        url = f"http://{host}:{port}"
    elif host:
        url = f"http://{host}"

    while url and not shutdown_event.is_set():
        try:
            print("Connecting to %s" %url)
            await sio.connect(url)
            break
        except:
            await asyncio.sleep(1)
    while not shutdown_event.is_set():
        await asyncio.sleep(1)


host = None
port = None
shutdown_event = Event()
sio = socketio.AsyncClient(logger=True, ssl_verify=False)
target_path = None

def run():
    global host
    global port
    global shutdown_event
    global target_path

    args = parse_cmd_args()
    host = args.get('host')
    port = args.get('port')
    target_path = args.get(
        'target',
        os.environ.get('MASCOPE_PRIVATE_DOWNLOADER_DIR', '.')
        )

    streamer = TofDaqStreamer(
        shutdown_event=shutdown_event,
    )
    streamer.start()

    loop = asyncio.get_event_loop()
    loop.create_task(streamer_processor(streamer))

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        shutdown_event.set()
    except Exception as e:
        print(e)
        shutdown_event.set()


if __name__ == '__main__':
    run()