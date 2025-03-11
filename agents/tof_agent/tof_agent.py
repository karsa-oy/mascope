import asyncio
import os
import sys
import threading
import textwrap

from multiprocessing import Event
from queue import Empty
import socketio


from mascope_runtime import Runtime
from mascope_sdk import api_post_file
from mascope_hardware.runtime import init as init_hardware_runtime


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

    [tof-agent]
    # meta
    log_level = 'info'
    log_path = './logs'
    # settings
    host = 'localhost'
    access_token = ''

    [hardware-lib]
    # meta
    log_level = 'info'
    log_path = './logs'
    # settings
    tofwerk_dll = 'Auto'
    #  TofWerk DLL selection - 'Auto', 'Windows', 'Linux' or 'Darwin' (= MacOs)
    """
)

FILE_UPLOAD_SIZE_LIMIT = 200 * 1024 * 1024  # 200 MB
HOST = None
PORT = None
URL = None
SHUTDOWN_EVENT = Event()

runtime = None
sio = socketio.AsyncClient(logger=False, ssl_verify=False)


def upload_sample_file(filepath: str) -> None:
    """Upload the acquired file to Mascope server using Mascope API

    :param filepath: Full path to the file to be uploaded
    :type filepath: str
    :raises Exception: Raises an exception if the request fails (status code != 200)
    """

    # Validate file before upload request
    # file extension
    file_ext = os.path.splitext(filepath)[1]
    if file_ext != ".h5":
        raise ValueError(f"{file_ext} is not an allowed file extension!")
    # file size
    file_size = os.stat(filepath).st_size
    if file_size > FILE_UPLOAD_SIZE_LIMIT:
        raise ValueError(
            f"File size ({round(file_size / (1024 * 1024), 1)} MB) exceeds the maximum allowed size ({FILE_UPLOAD_SIZE_LIMIT / (1024 * 1024)} MB)"
        )

    # Make file upload request
    resp = api_post_file(
        url=URL,
        path="sample/files/upload",
        access_token=runtime.config.access_token,
        filepath=filepath,
    )

    if resp is not None:
        runtime.logger.info(
            f"File upload of file {os.path.basename(filepath)} succeeded!"
        )
    else:
        raise Exception(f"File upload failed for file {os.path.basename(filepath)}")


async def streamer_processor(streamer) -> None:
    """Streamer processor task

    Monitors the TofDaqStreamer instance, and streams notifications to the server
    about the status. When the acquisition is completed, uploads the file.

    :param streamer: Streamer instance
    :type streamer: TofDaqStreamer
    :return: Returns nothing
    :rtype: None
    """

    async def handle_spec_data(data: dict) -> None:
        """Handle spectrum data from the streamer

        Updates the log and emits notifications to the server about stream progress.

        :param data: Input data from the streamer
        :type data: dict
        :return: Returns nothing
        :rtype: None
        """
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
            try:
                # Spawn a thread for file upload to not block the processing of subsequent acquisitions
                upload_thread = threading.Thread(
                    target=upload_sample_file, args=(raw_filename,), daemon=True
                )
                upload_thread.start()
            except Exception as e:
                runtime.logger.error(f"Failed to upload acquired file: {e}")
            if sio.connected:
                await sio.emit(
                    "instrument_acquisition_finished",
                    notification_data,
                    namespace="/tof-agent",
                )
        elif spec_i < 0:
            # New file
            runtime.logger.info(f"New file: {filename}")
            if sio.connected:
                await sio.emit(
                    "instrument_acquisition_started",
                    notification_data,
                    namespace="/tof-agent",
                )
        else:
            # New data to existing file
            if sio.connected:
                await sio.emit(
                    "instrument_acquisition_progress",
                    notification_data,
                    namespace="/tof-agent",
                )
        runtime.logger.info(f"{streamer.progress:.2f}")

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

    # Main processing loop
    while not streamer.shutdown_event.is_set():
        try:
            # Check the queue for new data
            spec_data = streamer.spec_queue.get_nowait()
            # Format filename
            spec_data.update({"filename": format_filename(spec_data)})
            # Handle spectrum data
            await handle_spec_data(spec_data)
        except Empty:
            await asyncio.sleep(0.1)
        except Exception as e:
            runtime.logger.error(f"Failed to process data from the TOF streamer: {e}")


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
        def mkdir(*args):
            path = os.path.join(*args)
            if not os.path.exists(path):
                os.makedirs(path)
            return path

        # set MASCOPE_PATH as %AppData%\Mascope\TOF_Agent
        mascope_path = mkdir(os.environ["APPDATA"], "Mascope", "TofAgent")
        os.environ.setdefault("MASCOPE_PATH", mascope_path)
        # setup runtime environment
        env_path = mkdir(mascope_path, "runtime", "env", "prod")
        mkdir(env_path, "logs")
        # init config files if they don't exists
        config_paths = [
            os.path.join(env_path, "base.mascope.toml"),
            os.path.join(env_path, "prod.mascope.toml"),
        ]
        for path in config_paths:
            if not os.path.exists(path):
                with open(path, "w", encoding="utf8") as file:
                    file.write(DEFAULT_CONFIG)
        # initialize the runtime in production mode
        opts = dict(env="prod", mode="prod", path=mascope_path)
        runtime = Runtime("tof-agent", **opts)
        init_hardware_runtime(**opts, context="tof-agent")
    else:
        # dev mode
        # runtime state inherited from the CLI
        runtime = Runtime("tof-agent")
        init_hardware_runtime(context="tof-agent")
    # Check if API access token is left empty
    if not runtime.config.access_token:
        raise Exception("Please enter your API access token in the config!")


async def main() -> None:
    """Main task

    Connect socket with the server and wait for shutdown event
    """
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
    while not SHUTDOWN_EVENT.is_set():
        try:
            runtime.logger.info(f"Connecting to {URL}")
            await sio.connect(
                url=URL,
                headers={"X-Service-Name": "tof-agent"},
                auth={"access_token": runtime.config.access_token},
                namespaces=["/tof-agent"],
            )
            runtime.logger.info("Connected!")
            break
        except Exception as e:
            runtime.logger.error(
                f"Failed to connect: {e}. Please try to refresh TOF agent access token in the configuration file."
            )
            # Try again in a second
            await asyncio.sleep(1)

    while not SHUTDOWN_EVENT.is_set():
        await asyncio.sleep(1)


def run() -> None:
    """Run method

    Initializes TofDaqStreamer thread, processor task and the main task.
    Then waits for keyboard interrupt.
    """

    # Initialize runtime
    initialize()
    # TofDaqStreamer has to be imported after runtime initialization
    from mascope_hardware.tofwerk.tof_streamer import TofDaqStreamer

    global HOST
    global PORT

    PORT = runtime.meta.api_port
    HOST = runtime.config.host

    # Initialize streamer thread
    streamer = TofDaqStreamer(
        shutdown_event=SHUTDOWN_EVENT,
    )
    streamer.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create streamer processor task
    loop.create_task(streamer_processor(streamer))

    try:
        # Run main task until shutdown event
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        SHUTDOWN_EVENT.set()
    except Exception as e:
        runtime.logger.error(f"Encountered an error: {e}")
        SHUTDOWN_EVENT.set()


if __name__ == "__main__":
    run()
