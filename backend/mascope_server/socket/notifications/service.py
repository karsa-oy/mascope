"""Socket.IO notification service."""

from copy import deepcopy
from mascope_server.socket.server import sio
from mascope_server.socket.notifications.schemas import UserNotification


async def emit_user_notification(
    notification: UserNotification = None,
    room_id: str = None,
    sid: str = None,
):
    """
    Utility function to emit a Socket.IO event to a specified room_id.

    :param notification: The notification to send with the event.
    :param room_id: The room to which the event should be emitted.
    :param sid: Optional. The session ID of the client. Used to send direct messages if needed.
    """
    notification_dict = notification.model_dump(exclude_none=True)
    if room_id:
        await sio.emit(
            "user_notification", notification_dict, room=room_id, namespace="/"
        )

    # Check if the user has moved from the room; if so, send them a direct message
    if sid and room_id != sid and room_id not in sio.rooms(sid, namespace="/"):
        await sio.emit("user_notification", notification_dict, room=sid, namespace="/")


async def send_progress_user_notification(
    notification: UserNotification, increment: float = None
):
    # Create a deep copy of the notification to ensure the original is not modified
    notification_copy = deepcopy(notification)

    # Extract internal metadata and clean up the data dictionary
    room_ids = notification_copy.data.pop("_room_ids", [])
    instrument_room = notification_copy.data.pop("_instrument_room", None)
    sid = notification_copy.data.pop("_sid", None)

    total_samples = notification_copy.data.pop("_total_samples", None)
    item_index = notification_copy.data.pop("_item_index", None)

    # total_batches = notification_copy.data.pop("_total_batches", None)
    batch_weight = notification_copy.data.pop("_batch_weight", None)
    batch_index = notification_copy.data.pop("_batch_index", None)

    # Clear any keys that start with an underscore as they are meant for internal use only
    keys_to_remove = [
        key for key in notification_copy.data.keys() if key.startswith("_")
    ]
    for key in keys_to_remove:
        notification_copy.data.pop(key, None)

    # If no other data remains, set data to None
    if not notification_copy.data:
        notification_copy.data = None

    # Calculate progress based on the notification type and provided increment
    if (
        notification_copy.type
        in [
            "match_compute_sample",
            "calibration_mz_fit",
            "calibration_mz_apply",
            "calibration_mz_calibrate_sample",
            "import_sample_items",
            "process_sample_item",
            "copy_sample_item",
        ]
        and increment
    ):
        notification_copy.progress = increment * 100
    if notification_copy.type == "match_compute_batch":
        if total_samples is not None and item_index is not None:
            notification_copy.progress = (
                (item_index + increment) / total_samples
            ) * 100

            notification_copy.message = f"Computing sample batch matches, processing sample {item_index + 1}/{total_samples}"
    if notification_copy.type == "rematch_batches":
        notification_copy.progress = (batch_index - 1 + increment) * batch_weight * 100
    if notification_copy.type == "sample_batch_export_peaks":
        if total_samples is not None and item_index is not None:
            notification_copy.progress = (
                (item_index + increment) / total_samples
            ) * 100
            notification_copy.message = f"Exporting peak data, processing sample {item_index + 1}/{total_samples}"

    if notification_copy.type == "copy_sample_batch":
        if total_samples is not None and item_index is not None:
            notification_copy.progress = (
                (item_index + increment) / total_samples
            ) * 100

            notification_copy.message = (
                f"Copying sample {item_index + 1}/{total_samples} to new batch."
            )
    # Emit the notification to all specified rooms
    for room_id in room_ids:
        await emit_user_notification(notification_copy, room_id, sid)
    # for istrument room don't check if the user has moved from the room -> no sid is provided
    if instrument_room:
        await emit_user_notification(notification_copy, instrument_room)


# TODO_notification delete after refactoring
async def emit_sio_event(
    event_name: str,
    notification: dict = None,
    room: str = None,
    sid: str = None,
):
    """
    Utility function to emit a Socket.IO event to a specified room.

    :param event_name: The name of the Socket.IO event to emit.
    :param notification: The notification to send with the event.
    :param room: The room to which the event should be emitted.
    :param sid: Optional. The session ID of the client. Used to send direct messages if needed.
    """
    # Emit without notification if event_name ends with '_reload'
    if event_name.endswith("_reload"):
        await sio.emit(event_name, room=room, namespace="/")
    else:
        # Emit the event to the specified room
        await sio.emit(event_name, notification, room=room, namespace="/")

        # Check if the user has moved from the room; if so, send them a direct message
        if sid and room != sid and room not in sio.rooms(sid, namespace="/"):
            await sio.emit(event_name, notification, room=sid, namespace="/")


async def handle_reloads(reload_events, kwargs, result):
    """Emit reload events based on the given configurations."""
    for event_name, room in reload_events:
        room_id = kwargs.get(room)
        if not room_id and result:
            room_id = result.get(room) or result.get("data").get(room)
        if room_id is not None:
            await sio.emit(event_name, room=room_id, namespace="/")


async def handle_notifications(rooms, notification, kwargs, result, sid):
    """Emit notifications to specified rooms."""
    for room in rooms:
        room_id = kwargs.get(room)
        if not room_id and result:
            # TODO_data wrapper
            room_id = (
                result.get(room)
                or result.get("data", {}).get(room)
                or result.get("_notification_data", {}).get(room)
            )
        # for istrument room don't check if the user has moved from the room -> no sid is provided
        if room_id and room == "instrument":
            await emit_user_notification(notification, room_id)
        if room_id is not None and room != "instrument":
            await emit_user_notification(notification, room_id, sid)
