from mascope_backend.socket import sio
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
    user_id = error_data.get("user_id")
    instrument = error_data.get("instrument")
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

    await emit_user_notification(
        notification=file_processing_notification, user_id=user_id
    )


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def file_processing_progress(sid, progress_data):
    """Handle file processing progress events from file converter service."""
    user_id = progress_data.get("user_id")
    instrument = progress_data.get("instrument")
    filename = progress_data.get("filename")
    progress = progress_data.get("progress", 0.0)

    file_processing_notification = UserNotification(
        process_id=file_processing_notification_process_id,
        type="file_processing",
        status="pending",
        message=f"Processing {filename}: {progress:.1f}%",
        data={
            "instrument": instrument,
            "filename": filename,
        },
        progress=progress,
    )

    await emit_user_notification(
        notification=file_processing_notification, user_id=user_id
    )


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def file_processing_success(sid, success_data):
    """Handle file processing success events from file converter service."""
    user_id = success_data.get("user_id")
    instrument = success_data.get("instrument")
    filename = success_data.get("filename")

    file_processing_notification = UserNotification(
        process_id=file_processing_notification_process_id,
        type="file_processing",
        status="success",
        message=f"Successfully processed {filename}",
        data={
            "instrument": instrument,
            "filename": filename,
        },
        progress=100,
    )

    await emit_user_notification(
        notification=file_processing_notification, user_id=user_id
    )
