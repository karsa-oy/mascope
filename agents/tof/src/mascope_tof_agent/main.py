import asyncio
import os
import shutil
import sys
import threading
import textwrap

from multiprocessing import Event
from queue import Empty
import socketio

from mascope_runtime import Runtime

from mascope_sdk import api_post_file
import socketio.exceptions

# TofDaqStreamer is imported in the run method after runtime initialization
# from mascope_tofwerk.tof_streamer import TofDaqStreamer


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
    color = "pink"
    # settings
    host = 'localhost'
    access_token = ''

    [tofwerk-lib]
    tags = ['lib']
    log_path = './logs'
    color = "white"
    # settings
    tofwerk_dll = 'Auto'
    #  TofWerk DLL selection - 'Auto', 'Windows', 'Linux' or 'Darwin' (= MacOs)
    """
)

FILE_UPLOAD_SIZE_LIMIT = 2.5 * 1024**3  # 2.5 GB
HOST = None
PORT = None
URL = None
SHUTDOWN_EVENT = Event()

runtime = None  # pylint: disable=invalid-name
sio = socketio.AsyncClient(logger=False, ssl_verify=False)


def process_file_upload(filepath: str) -> None:
    """Process file upload

    :param filepath: Full path to the file to be uploaded
    :type filepath: str
    """
    try:
        upload_sample_file(filepath)
    except Exception as e:  # pylint: disable=broad-except
        runtime.logger.error(f"Exception {e.__class__.__name__}({str(e)})")
        # Move failed file into a separate directory
        source_dir = os.path.dirname(filepath)
        failed_dir = os.path.join(source_dir, "failed_uploads")
        failed_filepath = os.path.join(failed_dir, os.path.basename(filepath))
        shutil.copyfile(filepath, failed_filepath)
        runtime.logger.debug(f"Moved failed file to {failed_filepath}")


def upload_sample_file(filepath: str) -> None:
    """Upload the acquired file to Mascope server using Mascope API

    :param filepath: Full path to the file to be uploaded
    :type filepath: str
    :raises Exception: Raises an exception if the request fails (status code != 200)
    """

    # Validate file before upload request
    # file extension
    file_ext = os.path.splitext(filepath)[1].lower()
    if file_ext != ".h5":
        raise ValueError(f"{file_ext} is not an allowed file extension!")
    # file size
    file_size = os.stat(filepath).st_size
    if file_size > FILE_UPLOAD_SIZE_LIMIT:
        raise ValueError(
            (
                f"File size ({round(file_size / (1024**3), 1)} GB) exceeds the maximum",
                f"allowed size ({FILE_UPLOAD_SIZE_LIMIT / (1024**3)} GB)",
            )
        )

    # Make file upload request
    runtime.logger.debug(f"Making an upload request to {URL} for file {filepath}")
    resp = api_post_file(
        url=URL,
        path="sample/files/upload",
        access_token=runtime.config.access_token,
        filepath=filepath,
        service_name="tof-agent",
    )

    if resp is not None:
        runtime.logger.info(
            f"File upload of file {os.path.basename(filepath)} succeeded!"
        )
    else:
        raise RuntimeError(f"File upload failed for file {os.path.basename(filepath)}")


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


def initialize() -> None:
    """Initialize the application and runtime depending on dev/prod mode

    If in prod mode, check if runtime directory structure exists, and create if not.

    :return: Return nothing
    :rtype: None
    """
    global runtime  # pylint: disable=global-statement
    # check if we are running in a pyinstaller bundle
    bundled = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    if bundled:
        # prod mode
        # set MASCOPE_PATH as %AppData%\Mascope\TOF_Agent
        mascope_path = mkdir(os.environ["APPDATA"], "Mascope", "TofAgent")
        os.environ.setdefault("MASCOPE_PATH", mascope_path)
        # setup runtime environment
        env_path = mkdir(mascope_path, ".runtime", "env", "prod")
        mkdir(env_path, "logs")
        # init config files if they don't exists
        config_paths = [
            os.path.join(env_path, "base.mascope.toml"),
            os.path.join(env_path, "prod.mascope.toml"),
        ]
        for path in config_paths:
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as file:
                    file.write(DEFAULT_CONFIG)
        # initialize the runtime in production mode
        runtime = Runtime("tof-agent", env="prod", mode="prod", path=mascope_path)
    else:
        # dev mode
        # runtime state inherited from the CLI
        runtime = Runtime("tof-agent")


async def streamer_processor(streamer) -> None:
    """Streamer processor task

    Monitors the TofDaqStreamer instance, and streams notifications to the server
    about the status. When the acquisition is completed, uploads the file.

    :param streamer: Streamer instance
    :type streamer: TofDaqStreamer
    :return: Returns nothing
    :rtype: None
    """

    async def process_streamer_data(data: dict) -> None:
        """Handle data from the streamer

        Updates the log and emits notifications to the server about stream progress.

        :param data: Input data from the streamer
        :type data: dict
        :return: Returns nothing
        :rtype: None
        """
        filename = data["filename"]
        instrument_name = filename.split("_")[0]
        spec_i = data["i"]  # scan index
        notification_data = {
            "filename": filename,
            "instrument": instrument_name,
            "progress": streamer.progress,
        }
        match spec_i:
            case None:
                # File finished
                runtime.logger.info(f"Acquisition of file {filename} finished")
                raw_filename = data["source_filepath"]
                # Spawn a thread for upload to not block processing of subsequent acquisitions
                upload_thread = threading.Thread(
                    target=process_file_upload, args=(raw_filename,), daemon=True
                )
                upload_thread.start()
                if sio.connected:
                    await sio.emit(
                        "instrument_acquisition_finished",
                        notification_data,
                        namespace="/tof-agent",
                    )
            case -1:
                # New file
                runtime.logger.info(f"Acquisition of file: {filename} started")
                if sio.connected:
                    await sio.emit(
                        "instrument_acquisition_started",
                        notification_data,
                        namespace="/tof-agent",
                    )
            case _:
                # New data to existing file
                if sio.connected:
                    await sio.emit(
                        "instrument_acquisition_progress",
                        notification_data,
                        namespace="/tof-agent",
                    )
        runtime.logger.info(f"Acquisition progress: {streamer.progress:.2f}%")

    # Main processing loop
    while not streamer.shutdown_event.is_set():
        try:
            # Check the queue for new data
            data = streamer.notification_queue.get_nowait()
            # Handle spectrum data
            await process_streamer_data(data)
        except Empty:
            # No new data, try again soon
            await asyncio.sleep(0.1)
        except Exception as e:  # pylint: disable=broad-except
            runtime.logger.error(f"Failed to process data from the TOF streamer: {e}")


async def main() -> None:
    """Main task

    Connect socket with the server and wait for shutdown event
    """
    # Socket connect loop
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
        except socketio.exceptions.ConnectionError as e:
            runtime.logger.error(
                f"Failed to connect: {e}. Please check the agent configuration."
            )
        # Try again in a moment
        runtime.logger.info("Retry connecting in 10 seconds...")
        await asyncio.sleep(10)

    # Wait until shutdown event
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
    from mascope_tofwerk.tof_streamer import (  # pylint: disable=import-outside-toplevel
        TofDaqStreamer,
    )

    global URL  # pylint: disable=global-statement
    global HOST  # pylint: disable=global-statement
    global PORT  # pylint: disable=global-statement

    PORT = runtime.meta.api_port
    HOST = runtime.config.host
    if HOST and PORT:
        URL = f"http://{HOST}:{PORT}"
    elif HOST:
        URL = f"http://{HOST}"
    if not URL:
        runtime.logger.error(
            "Mascope host not defined, please check configuration. Exiting..."
        )
        raise RuntimeError("Mascope host not defined, please check configuration.")

    # Initialize streamer thread
    try:
        streamer = TofDaqStreamer(
            shutdown_event=SHUTDOWN_EVENT,
        )
        streamer.start()
    except RuntimeError as e:
        runtime.logger.error(f"Failed to initialize TofDaqStreamer: {e}")
        return

    # Create streamer processor task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(streamer_processor(streamer))

    try:
        # Run main task until shutdown event
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        runtime.logger.info("Keyboard interrupt received")
    except Exception as e:  # pylint: disable=broad-except
        runtime.logger.error(f"Encountered an error: {e}")
    finally:
        runtime.logger.info("Shutting down...")
        SHUTDOWN_EVENT.set()


if __name__ == "__main__":
    run()
