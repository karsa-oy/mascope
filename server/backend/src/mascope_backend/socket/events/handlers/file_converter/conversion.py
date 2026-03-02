from mascope_backend.db.id import gen_id
from mascope_backend.socket import sio
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


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def peak_detection_progress(sid, data):
    """Handle peak detection progress events from the file converter service.

    Emitted periodically while peak detection is running.
    """
    user_id = data.get("user_id")
    filename = data.get("filename")
    sample_file_id = data.get("sample_file_id")
    process_id = data.get("process_id")
    progress = data.get("progress", 0)

    notification = UserNotification(
        process_id=process_id,
        type="compute_sample_file_peaks",
        status="pending",
        message=f"Peak detection for '{filename}': {progress}%",
        data={
            "filename": filename,
            "sample_file_id": sample_file_id,
        },
        progress=progress,
    )

    await emit_user_notification(notification=notification, user_id=user_id)


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def peak_detection_complete(sid, data):
    """Handle peak detection completion events from the file converter service.

    Emitted when a peak detection request finishes successfully.
    """
    user_id = data.get("user_id")
    filename = data.get("filename")
    sample_file_id = data.get("sample_file_id")
    process_id = data.get("process_id")

    notification = UserNotification(
        process_id=process_id,
        type="compute_sample_file_peaks",
        status="success",
        message=f"Peak detection completed for '{filename}'.",
        data={
            "filename": filename,
            "sample_file_id": sample_file_id,
        },
        progress=100,
    )

    await emit_user_notification(notification=notification, user_id=user_id)


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def peak_detection_error(sid, data):
    """Handle peak detection error events from the file converter service.

    Emitted when a delegated peak detection fails or is rejected
    (as repeated for the same sample file).
    """
    user_id = data.get("user_id")
    filename = data.get("filename")
    sample_file_id = data.get("sample_file_id")
    process_id = data.get("process_id")
    error_message = data.get("error", "Unknown peak detection error")
    status = data.get("status", "error")

    if status == "warning":
        notification = UserNotification(
            process_id=process_id,
            type="compute_sample_file_peaks",
            status="warning",
            message=error_message,
            data={
                "filename": filename,
                "sample_file_id": sample_file_id,
            },
        )
    else:
        notification = UserNotification(
            process_id=process_id,
            type="compute_sample_file_peaks",
            status="error",
            message=f"Peak detection failed for '{filename}': {error_message}",
            data={
                "filename": filename,
                "sample_file_id": sample_file_id,
            },
            error={
                "message": error_message,
            },
        )

    await emit_user_notification(notification=notification, user_id=user_id)
