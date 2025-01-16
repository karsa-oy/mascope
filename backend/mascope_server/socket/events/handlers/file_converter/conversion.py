from mascope_server.socket.server import sio
from mascope_server.db.id import gen_id
from mascope_server.socket.auth.decorators import file_converter_socket_auth
from mascope_server.socket.notifications import (
    UserNotification,
    emit_user_notification,
)

file_conversion_notification_process_id = gen_id(8)


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def file_conversion_started(sid, conversion_data):
    instrument = conversion_data.get("instrument")
    filename = conversion_data.get("filename")

    instrument_conversion_notification = UserNotification(
        process_id=file_conversion_notification_process_id,
        type="instrument_conversion",
        status="pending",
        message=f"Conversion {filename}",
        progress=0,
        data={
            "instrument": instrument,
            "filename": filename,
        },
    )

    await emit_user_notification(instrument_conversion_notification, instrument)


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def file_conversion_progress(sid, conversion_data):
    instrument = conversion_data.get("instrument")
    filename = conversion_data.get("filename")
    progress = conversion_data.get("progress")

    instrument_conversion_notification = UserNotification(
        process_id=file_conversion_notification_process_id,
        type="instrument_conversion",
        status="pending",
        message=f"Conversion {filename}",
        progress=progress,
        data={
            "instrument": instrument,
            "filename": filename,
        },
    )

    await emit_user_notification(instrument_conversion_notification, instrument)


@sio.event(namespace="/file-converter")
@file_converter_socket_auth(minimum_role="editor")
async def file_conversion_finished(sid, conversion_data):
    instrument = conversion_data.get("instrument")
    filename = conversion_data.get("filename")
    progress = conversion_data.get("progress", 100)

    instrument_conversion_notification = UserNotification(
        process_id=file_conversion_notification_process_id,
        type="instrument_conversion",
        status="success",
        message=f"Conversion of file {filename} completed.",
        progress=progress,
        data={
            "instrument": instrument,
            "filename": filename,
        },
    )

    await emit_user_notification(instrument_conversion_notification, instrument)
