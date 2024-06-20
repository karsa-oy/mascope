from mascope_server.api_sio import sio
from mascope_server.db.id import gen_id
from mascope_server.api.models.pydantic_models.user_notification_pydantic_model import (
    UserNotification,
)
from mascope_server.api.utils import api_features


instrument_acquisition_notification_process_id = gen_id(8)
instrument_conversion_notification_process_id = gen_id(8)


@sio.event(namespace="/")
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

    await api_features.emit_user_notification(
        instrument_acquisition_notification, instrument
    )


@sio.event(namespace="/")
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

    await api_features.emit_user_notification(
        instrument_acquisition_notification, instrument
    )


@sio.event(namespace="/")
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

    await api_features.emit_user_notification(
        instrument_acquisition_notification, instrument
    )


@sio.event(namespace="/")
async def instrument_conversion_started(sid, conversion_data):
    instrument = conversion_data.get("instrument")
    filename = conversion_data.get("filename")

    instrument_conversion_notification = UserNotification(
        process_id=instrument_conversion_notification_process_id,
        type="instrument_conversion",
        status="pending",
        message=f"Conversion {filename}",
        progress=0,
        data={
            "instrument": instrument,
            "filename": filename,
        },
    )

    await api_features.emit_user_notification(
        instrument_conversion_notification, instrument
    )


@sio.event(namespace="/")
async def instrument_conversion_progress(sid, conversion_data):
    instrument = conversion_data.get("instrument")
    filename = conversion_data.get("filename")
    progress = conversion_data.get("progress")

    instrument_conversion_notification = UserNotification(
        process_id=instrument_conversion_notification_process_id,
        type="instrument_conversion",
        status="pending",
        message=f"Conversion {filename}",
        progress=progress,
        data={
            "instrument": instrument,
            "filename": filename,
        },
    )

    await api_features.emit_user_notification(
        instrument_conversion_notification, instrument
    )


@sio.event(namespace="/")
async def instrument_conversion_finished(sid, conversion_data):
    instrument = conversion_data.get("instrument")
    filename = conversion_data.get("filename")
    progress = conversion_data.get("progress", 100)

    instrument_conversion_notification = UserNotification(
        process_id=instrument_conversion_notification_process_id,
        type="instrument_conversion",
        status="success",
        message=f"Conversion of file {filename} completed.",
        progress=progress,
        data={
            "instrument": instrument,
            "filename": filename,
        },
    )

    await api_features.emit_user_notification(
        instrument_conversion_notification, instrument
    )
