from mascope_backend.socket.server import sio
from mascope_backend.db.id import gen_id
from mascope_backend.socket.auth.decorators import socket_auth
from mascope_backend.socket.notifications import (
    UserNotification,
    emit_user_notification,
)


instrument_acquisition_notification_process_id = gen_id(8)


@sio.event(namespace="/tof-agent")
@socket_auth(minimum_role="editor", service_name="tof-agent")
async def instrument_acquisition_started(sid: str, acquisition_data: dict):
    """Handle the start of an instrument acquisition.

    This event is triggered by TofAgent when an instrument acquisition starts, and it emits
    a user notification with the acquisitions details.

    :param sid: The session ID of the client.
    :type sid: str
    :param acquisition_data: A dictionary containing details about the acquisition,
                            including instrument name, filename, and polarity.
    :type acquisition_data: dict
    """
    instrument = acquisition_data["instrument"]
    filename = acquisition_data["filename"]
    polarity = acquisition_data["polarity"]

    instrument_acquisition_notification = UserNotification(
        process_id=instrument_acquisition_notification_process_id,
        type="instrument_acquisition",
        status="pending",
        message=f"Acquisition {filename} ({instrument})",
        progress=0,
        data={"instrument": instrument, "filename": filename, "polarity": polarity},
    )

    await emit_user_notification(instrument_acquisition_notification, instrument)


@sio.event(namespace="/tof-agent")
@socket_auth(minimum_role="editor", service_name="tof-agent")
async def instrument_acquisition_progress(sid: str, acquisition_data: dict):
    """Handle the progress of an instrument acquisition.

    This event is triggered by TofAgent to update the progress of an ongoing instrument
    acquisition.

    :param sid: The session ID of the client.
    :type sid: str
    :param acquisition_data: A dictionary containing details about the acquisition,
                            including instrument name, filename, and progress percentage.
    :type acquisition_data: dict
    """

    instrument = acquisition_data["instrument"]
    filename = acquisition_data["filename"]
    progress = acquisition_data["progress"]

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
async def instrument_acquisition_finished(sid: str, acquisition_data: dict):
    """Handle the completion of an instrument acquisition.

    This event is triggered by TofAgent when an instrument acquisition is completed,
    and it emits a user notification with the acquisition details.

    :param sid: The session ID of the client.
    :type sid: str
    :param acquisition_data: A dictionary containing details about the acquisition,
                            including instrument name, filename, and progress percentage.
    :type acquisition_data: dict
    """

    instrument = acquisition_data["instrument"]
    filename = acquisition_data["filename"]
    progress = acquisition_data["progress"]

    instrument_acquisition_notification = UserNotification(
        process_id=instrument_acquisition_notification_process_id,
        type="instrument_acquisition",
        status="success",
        message=f"Acquisition of file {filename} completed, instrument {instrument}.",
        progress=progress,
        data={"instrument": instrument, "filename": filename},
    )

    await emit_user_notification(instrument_acquisition_notification, instrument)
