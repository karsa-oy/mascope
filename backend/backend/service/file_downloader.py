import argparse
import asyncio
import os
import sys
import shutil
from dotenv import load_dotenv
from multiprocessing import Event, Queue
from queue import Empty

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
from backend.service.lib.filesystem_watcher import FSWatcher
from backend.service.lib.util import load_env_yaml

file_queue = Queue()
shutdown_event = Event()
target_path = None


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
        "-m", "--file_mask",
        help="filename mask",
        type=str, required=False
    )
    parser.add_argument(
        "-r", "--recursive",
        help="recursive",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "-s", "--source_dir",
        help="source directory",
        type=str, required=False
    )
    parser.add_argument(
        "-t", "--target_dir",
        help="target directory",
        type=str, required=False
    )
    parser.add_argument(
        "-p", "--ping",
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
    global file_queue
    global shutdown_event
    global target_path
    while not shutdown_event.is_set():
        try:
            file_to_download = file_queue.get_nowait()
            filename = os.path.basename(file_to_download)
            shutil.move(file_to_download, os.path.join(target_path, filename))
        except Empty:
            await asyncio.sleep(1)


def run():
    global file_queue
    global shutdown_event
    global target_path

    args = parse_cmd_args()
    print(args)
    loop = asyncio.get_event_loop()

    source_path = args['source_dir']
    file_mask = args.get('file_mask', '*')
    target_path = args['target_dir']
    recursive = args['recursive']
    ping = args['ping']

    if not os.path.exists(source_path):
        print(f"Creating missing source directory {source_path}")
        os.makedirs(source_path)

    if not os.path.exists(target_path):
        print(f"Creating missing target directory {target_path}")
        os.makedirs(target_path)

    fs_watcher = FSWatcher(
        path=source_path,
        mask=file_mask,
        file_queue=file_queue,
        recursive=recursive,
        ping=ping,
        shutdown_event=shutdown_event,
        )
    fs_watcher.run_as_daemon()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        shutdown_event.set()
    except Exception as e:
        print(e)
        shutdown_event.set()


if __name__ == '__main__':
    load_dotenv()
    run()