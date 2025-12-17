"""Room subscription management with Redis tracking.

Handles subscribe/unsubscribe events for Socket.IO rooms with cross-worker
membership tracking. Each subscription:
1. Adds SID to Socket.IO room (for AsyncRedisManager pub/sub routing)
2. Records membership in Redis (for cross-worker presence queries)
"""

from mascope_backend.socket import sio
from mascope_backend.socket.auth.decorators import socket_auth
from mascope_backend.socket.storage import get_session_user, room_tracker


@sio.event(namespace="/")
@socket_auth(minimum_role="guest")
async def subscribe(sid, room):
    """
    Subscribe authenticated user to a room.

    Performs dual registration:
    - Socket.IO room (for event routing via AsyncRedisManager)
    - Redis tracking (for cross-worker membership queries)

    :param sid: Socket session ID
    :type sid: str
    :param room: Room identifier (e.g., "batch-123")
    :type room: str
    """
    # Get user_id from session
    session = await get_session_user(sid)
    user_id = session["user_id"]

    # Socket.IO room (AsyncRedisManager handles pub/sub routing)
    await sio.enter_room(sid, room)

    # Redis tracking (cross-worker membership queries)
    await room_tracker.join(user_id, room)


@sio.event(namespace="/")
@socket_auth(minimum_role="guest")
async def unsubscribe(sid, room):
    """
    Unsubscribe authenticated user from a room.

    Removes from both Socket.IO room and Redis tracking.

    :param sid: Socket session ID
    :type sid: str
    :param room: Room identifier
    :type room: str
    """
    # Get user_id from session
    session = await get_session_user(sid)
    user_id = session["user_id"]

    # Remove from Socket.IO room
    await sio.leave_room(sid, room)

    # Remove from Redis tracking
    await room_tracker.leave(user_id, room)
