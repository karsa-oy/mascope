import asyncio
import os
import shutil
import socketio

from multiprocessing import Event
from queue import Empty

from mascope_hardware.tofwerk.tof_streamer import TofDaqStreamer

import mascope_runtime as runtime

logger = runtime.logger.service("tof-agent")
sio_logger = runtime.logger.service("tof-agent", markup=False)


async def streamer_processor(streamer):
    global sio

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
            logger.info("File finished")
            raw_filename = data["source_filepath"]
            global target_path
            while True:
                try:
                    shutil.copyfile(
                        raw_filename,
                        os.path.join(target_path, os.path.basename(raw_filename)),
                    )
                    break
                except Exception as e:
                    logger.error("Failed to copy acquired file: %s" % e)
                    await sio.sleep(1)
            if sio.connected:
                await sio.emit(
                    "instrument_acquisition_finished",
                    notification_data,
                )
        elif spec_i < 0:
            # New file
            logger.info("New file: %s" % filename)
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
        logger.info("%.2f" % streamer.progress)
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
    global host
    global port
    global sio

    url = None
    if host and port:
        url = f"http://{host}:{port}"
    elif host:
        url = f"http://{host}"
    if not url:
        logger.warning("Mascope host not defined, running in offline mode")
    while url and not shutdown_event.is_set():
        try:
            logger.info(f"Connecting to {url}")
            await sio.connect(url)
            break
        except:
            await asyncio.sleep(1)
    while not shutdown_event.is_set():
        await asyncio.sleep(1)


host = None
port = None
shutdown_event = Event()
sio = socketio.AsyncClient(logger=False, ssl_verify=False)
target_path = None


def run():
    global host
    global port
    global shutdown_event
    global target_path

    config = runtime.mount()

    host = config.tof_agent.host
    port = config.tof_agent.port
    target_path = config.tof_agent.target

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
        logger.error(e)
        shutdown_event.set()


if __name__ == "__main__":
    run()
