from mascope_backend.socket.server import sio
from mascope_backend.db.id import gen_id
from mascope_backend.socket.auth.decorators import file_converter_socket_auth
from mascope_backend.socket.notifications import (
    UserNotification,
    emit_user_notification,
)

file_processing_notification_process_id = gen_id(8)


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def file_processing_error(sid, error_data):
    """Handle file processing error events from file converter service."""
    instrument = error_data.get("instrument")
    user_sid = error_data.get("user_sid")
    filename = error_data.get("filename")
    error_message = error_data.get("error", "Unknown processing error")

    file_processing_notification = UserNotification(
        process_id=file_processing_notification_process_id,
        type="file_processing",
        status="error",
        message=f"Failed to process {filename}: {error_message}",
        data={
            "instrument": instrument,
            "filename": filename,
        },
        error={
            "message": error_message,
        },
    )

    await emit_user_notification(file_processing_notification, user_sid)
