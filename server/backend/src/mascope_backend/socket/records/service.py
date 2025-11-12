"""Record synchronization event emission."""

from typing import Any
from mascope_backend.socket.server import sio
from mascope_backend.socket.records.schemas import RecordEvent
from mascope_backend.socket.records.config import record_sync_config
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime


async def emit_record_created(
    record_type: str,
    record_id: str,
    record: dict[str, Any],
    room: str | list[str] | None = None,
) -> None:
    """
    Emit record creation event.

    :param record_type: Record type (e.g., 'sample_batch')
    :param record_id: ID of created record
    :param record: Full record data
    :param room: Target room(s) or None to broadcast
    """
    event = RecordEvent(
        event_id=gen_id(record_sync_config.EVENT_ID_LENGTH),
        operation="created",
        record_type=record_type,
        record_id=record_id,
        record=record,
    )
    await _emit(event, room)


async def emit_record_updated(
    record_type: str,
    record_id: str,
    record: dict[str, Any],
    room: str | list[str] | None = None,
    changed_fields: list[str] | None = None,
) -> None:
    """
    Emit record update event.

    Supports both full and partial updates:
    - Full update: Send complete record data, changed_fields=None
    - Partial update: Send only changed fields in record dict, provide changed_fields list

    When changed_fields is provided, frontend merges fields into existing record
    instead of replacing it entirely. Use for bulk status updates or field-specific changes.

    :param record_type: Record type (e.g., 'sample_batch')
    :param record_id: ID of updated record
    :param record: Full or partial record data
    :param room: Target room(s) or None to broadcast
    :param changed_fields: List of field names that changed (enables partial merge)
    """
    event = RecordEvent(
        event_id=gen_id(record_sync_config.EVENT_ID_LENGTH),
        operation="updated",
        record_type=record_type,
        record_id=record_id,
        record=record,
        changed_fields=changed_fields,
    )
    await _emit(event, room)


async def emit_record_deleted(
    record_type: str,
    record_id: str,
    room: str | list[str] | None = None,
) -> None:
    """
    Emit record deletion event.

    :param record_type: Record type (e.g., 'sample_batch')
    :param record_id: ID of deleted record
    :param room: Target room(s) or None to broadcast
    """
    event = RecordEvent(
        event_id=gen_id(record_sync_config.EVENT_ID_LENGTH),
        operation="deleted",
        record_type=record_type,
        record_id=record_id,
        record=None,
    )
    await _emit(event, room)


async def emit_record_reload(
    record_type: str,
    record_id: str | None = None,
    room: str | list[str] | None = None,
) -> None:
    """
    Emit bulk reload event (signals frontend to perform full list reload via API).

    :param record_type: Record type to reload (e.g., 'sample_batch')
    :param record_id: Optional specific record ID (usually None for bulk reload)
    :param room: Optional target room(s)
    """
    event = RecordEvent(
        event_id=gen_id(record_sync_config.EVENT_ID_LENGTH),
        operation="reload",
        record_type=record_type,
        record_id=record_id,
    )
    await _emit(event, room)


async def _emit(event: RecordEvent, room: str | list[str] | None) -> None:
    """
    Emit event to room(s) or broadcast to all if room is None.

    :param event: Event to emit
    :param room: Target room(s), or None to broadcast to all connected clients
    """
    event_name = event.event_name()
    payload = event.model_dump(mode="json")

    # Broadcast to all if room is None
    if room is None:
        try:
            await sio.emit(event_name, payload, namespace="/")
            runtime.logger.debug(f"Broadcast {event_name} to all clients")
        except Exception as e:
            runtime.logger.error(f"Failed to broadcast {event_name}: {e}")
        return

    # Emit to specific room(s)
    rooms = [room] if isinstance(room, str) else room
    for room_id in rooms:
        try:
            await sio.emit(event_name, payload, room=room_id, namespace="/")
            runtime.logger.debug(f"Emitted {event_name} to {room_id}")
        except Exception as e:
            runtime.logger.error(f"Failed to emit {event_name} to {room_id}: {e}")
