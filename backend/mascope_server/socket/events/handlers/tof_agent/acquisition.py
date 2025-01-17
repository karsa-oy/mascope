from mascope_server.socket.server import sio
from mascope_server.db.id import gen_id
from mascope_server.socket.auth.decorators import socket_auth
from mascope_server.socket.notifications import (
    UserNotification,
    emit_user_notification,
)


instrument_acquisition_notification_process_id = gen_id(8)


@sio.event(namespace="/tof-agent")
@socket_auth(minimum_role="editor", service_name="tof-agent")
async def instrument_acquisition_started(sid, acquisition_data):
    instrument = acquisition_data.get("instrument")
    filename = acquisition_data.get("filename")

    instrument_acquisition_notification = UserNotification(
        process_id=instrument_acquisition_notification_process_id,
        type="instrument_acquisition",
        status="pending",
        message=f"Acquisition {filename} ({instrument})",
        progress=0,
        data={"instrument": instrument, "filename": filename},
    )

    await emit_user_notification(instrument_acquisition_notification, instrument)


@sio.event(namespace="/tof-agent")
@socket_auth(minimum_role="editor", service_name="tof-agent")
async def instrument_acquisition_progress(sid, acquisition_data):
    instrument = acquisition_data.get("instrument")
    filename = acquisition_data.get("filename")
    progress = acquisition_data.get("progress")

    instrument_acquisition_notification = UserNotification(
        process_id=instrument_acquisition_notification_process_id,
        type="instrument_acquisition",
        status="pending",
        message=f"Acquisition {filename} ({instrument})",
        progress=progress,
        data={"instrument": instrument, "filename": filename},
    )

    await emit_user_notification(instrument_acquisition_notification, instrument)


@sio.event(namespace="/tof-agent")
@socket_auth(minimum_role="editor", service_name="tof-agent")
async def instrument_acquisition_finished(sid, acquisition_data):
    instrument = acquisition_data.get("instrument")
    filename = acquisition_data.get("filename")
    progress = acquisition_data.get("progress", 100)

    instrument_acquisition_notification = UserNotification(
        process_id=instrument_acquisition_notification_process_id,
        type="instrument_acquisition",
        status="success",
        message=f"Acquisition of file {filename} completed, instrument {instrument}.",
        progress=progress,
        data={"instrument": instrument, "filename": filename},
    )

    await emit_user_notification(instrument_acquisition_notification, instrument)
