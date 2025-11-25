from mascope_backend.socket import sio
from mascope_backend.socket.emitter import event_emitter
from mascope_backend.runtime import runtime


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
