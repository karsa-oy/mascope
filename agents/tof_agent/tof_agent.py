import asyncio
import os
import shutil
import sys
import textwrap

from multiprocessing import Event
from queue import Empty
import socketio


from mascope_runtime import MascopeRuntimeModule
from mascope_hardware.runtime import init as init_hardware_runtime

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

    [tof-agent]
    # meta
    log_level = 'info'
    log_path = './logs'
    # settings
    host = 'localhost'
    target = './filestreams'

    [hardware-lib]
    # meta
    log_level = 'info'
    log_path = './logs'
    # settings
    tofwerk_dll = 'Auto'
    #  TofWerk DLL selection - 'Auto', 'Windows', 'Linux' or 'Darwin' (= MacOs)
    """
)


if bundled:
    # prod mode
    # set MASCOPE_PATH as %AppData%\Mascope\TOF_Agent
    mascope_path = mkdir(os.environ["APPDATA"], "Mascope", "TofAgent")
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
    opts = dict(env="prod", mode="prod", path=mascope_path)
    runtime = MascopeRuntimeModule("tof-agent", **opts)
    init_hardware_runtime(**opts)
else:
    # dev mode
    # runtime state inherited from the CLI
    runtime = MascopeRuntimeModule("tof-agent")
    init_hardware_runtime()


from mascope_hardware.tofwerk.tof_streamer import TofDaqStreamer


async def streamer_processor(streamer):
    # Handlers
    async def handle_spec_data(data):
        filename = data["filename"]
        instrument_name = filename.split("_")[0]
        spec_i = data["i"]
        notification_data = {
            "filename": filename,
            "instrument": instrument_name,
            "progress": streamer.progress,
        }
        if spec_i is None:
            # File finished
            runtime.logger.info("File finished")
            raw_filename = data["source_filepath"]
            while True:
                try:
                    shutil.copyfile(
                        raw_filename,
                        os.path.join(target_path, os.path.basename(raw_filename)),
                    )
                    break
                except Exception as e:
                    runtime.logger.error(f"Failed to copy acquired file: {e}")
                    await sio.sleep(1)
            if sio.connected:
                await sio.emit(
                    "instrument_acquisition_finished",
                    notification_data,
                )
        elif spec_i < 0:
            # New file
            runtime.logger.info(f"New file: {filename}")
            if sio.connected:
                await sio.emit(
                    "instrument_acquisition_started",
                    notification_data,
                )
        else:
            # New data to existing file
            if sio.connected:
                await sio.emit(
                    "instrument_acquisition_progress",
                    notification_data,
                )
        runtime.logger.info(f"{streamer.progress:.2f}")
        return True

    async def handle_tps_data(data):
        return

        # Main loop

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

    while not streamer.shutdown_event.is_set():
        try:
            # Check the queue for new data
            spec_data = streamer.spec_queue.get_nowait()
            # Format filename
            spec_data.update({"filename": format_filename(spec_data)})
            # Handle spectrum data
            success = await handle_spec_data(spec_data)
            if success and hasattr(streamer, "tps_queue"):
                tps_data = streamer.tps_queue.get()
                # Format filename
                tps_data.update({"filename": format_filename(tps_data)})
                await handle_tps_data(tps_data)
        except Empty:
            await asyncio.sleep(0.1)


async def main():
    global URL
    if HOST and PORT:
        URL = f"http://{HOST}:{PORT}"
    elif HOST:
        URL = f"http://{HOST}"
    if not URL:
        runtime.logger.error(
            "Mascope host not defined, please check configuration. Exiting..."
        )
        SHUTDOWN_EVENT.set()
    while URL and not SHUTDOWN_EVENT.is_set():
        try:
            runtime.logger.info(f"Connecting to {URL}")
            await sio.connect(URL)
            runtime.logger.info(f"Connected!")
            break
        except:
            await asyncio.sleep(1)

    while not SHUTDOWN_EVENT.is_set():
        await asyncio.sleep(1)


HOST = None
PORT = None
URL = None
SHUTDOWN_EVENT = Event()
sio = socketio.AsyncClient(logger=False, ssl_verify=False)
TARGET_PATH = None


def run():
    global HOST
    global PORT
    global TARGET_PATH

    PORT = runtime.meta.api_port
    HOST = runtime.config.host
    TARGET_PATH = runtime.config.target

    streamer = TofDaqStreamer(
        shutdown_event=SHUTDOWN_EVENT,
    )
    streamer.start()

    loop = asyncio.get_event_loop()
    loop.create_task(streamer_processor(streamer))

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        SHUTDOWN_EVENT.set()
    except Exception as e:
        runtime.logger.error(e)
        SHUTDOWN_EVENT.set()


if __name__ == "__main__":
    run()
