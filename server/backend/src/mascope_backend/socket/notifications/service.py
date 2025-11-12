"""Socket.IO notification service."""

from copy import deepcopy
from typing import Any
from mascope_backend.socket.server import sio
from mascope_backend.socket.notifications.schemas import UserNotification

from mascope_backend.runtime import runtime


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
            "copy_sample_items",
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


async def handle_notifications(
    rooms: list[str],
    notification: UserNotification,
    kwargs: dict[str, Any],
    result: dict[str, Any] | None,
    sid: str | None,
) -> None:
    """
    Emit Socket.IO user notifications to specified rooms.

    Process flow:
    1. Guard against empty rooms list
    2. For each room:
       - Find room_id in kwargs, result['data'], or result['_notification_data']
       - Handle special case for 'instrument' room
         TODO_notifications refactor this, looks like a hack
       - Emit notification to the room

    :param rooms: List of room keys to find room IDs
    :type rooms: list[str] | None
    :param notification: UserNotification instance to be emitted
    :type notification: UserNotification
    :param kwargs:  Controller function kwargs that may contain room IDs
    :type kwargs: dict[str, Any]
    :param result: Controller function result that may contain room IDs in 'data'
            or '_notification_data' keys. May be None when handling error notifications.
    :type result: dict[str, Any] | None
    :param sid: Socket.IO session ID for direct messaging
    :type sid: str | None
    """
    for room in rooms:
        # Step 1: Check if room_id is in kwargs
        room_id = kwargs.get(room)

        #  Step 2:Try to find room_id in result
        if not room_id and result:
            if isinstance(result, dict):
                # Try to find room_id directly in result
                if room in result:
                    room_id = result.get(room)

                # Check if 'data' exists and is a dictionary
                data = result.get("data")
                if room_id is None and isinstance(data, dict) and room in data:
                    room_id = data.get(room)

                # Check if '_notification_data' exists and is a dictionary
                notification_data = result.get("_notification_data")
                if (
                    room_id is None
                    and isinstance(notification_data, dict)
                    and room in notification_data
                ):
                    room_id = notification_data.get(room)
        if not room_id:
            runtime.logger.warning(
                f"No room ID found for user notification in room '{room}'"
            )
            continue
        # for istrument room don't check if the user has moved from the room -> no sid is provided
        if room_id and room == "instrument":
            await emit_user_notification(notification, room_id)
        if room_id is not None and room != "instrument":
            await emit_user_notification(notification, room_id, sid)
