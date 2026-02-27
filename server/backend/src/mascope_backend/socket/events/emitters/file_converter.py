from mascope_backend.runtime import runtime
from mascope_backend.socket import sio
from mascope_backend.socket.emitter import event_emitter


@event_emitter.on("file-converter.auth")
async def send_file_context_to_converter(data: dict):
    """
    Handle file-converter.auth events, emit socket events to file converter service.

    :param data: Dict containing file and user context
    :type data: dict
    """
    # Emit to file converter service
    runtime.logger.debug(f"Emitting file_context for {data['filename']}")

    await sio.emit("file_context", data, namespace="/file-converter")


@event_emitter.on("file-converter.peak_detection_request")
async def send_peak_detection_request_to_converter(data: dict):
    """
    Send a peak detection request to the file converter service via Socket.IO.

    Emitted when a user manually triggers peak detection from the backend API.
    The file converter will handle the actual compute_peaks call.

    :param data: Dict containing filename, sample_file_id, user_id, access_token
    :type data: dict
    """
    runtime.logger.debug(f"Emitting peak_detection_request for {data['filename']}")
    await sio.emit("peak_detection_request", data, namespace="/file-converter")
