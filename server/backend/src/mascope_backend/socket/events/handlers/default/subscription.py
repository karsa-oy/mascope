"""
Users room management.
"""

from mascope_backend.socket import sio
from mascope_backend.socket.auth.decorators import socket_auth


@sio.event(namespace="/")
@socket_auth(minimum_role="guest")
async def subscribe(sid, room):
    """
    Allow authenticated users to subscribe to a room.

    :param sid: Socket session ID
    :type sid: str
    :param room: Room to subscribe to
    :type room: str
    """
    await sio.enter_room(sid, room)


@sio.event(namespace="/")
@socket_auth(minimum_role="guest")
async def unsubscribe(sid, room):
    """
    Allow authenticated users to unsubscribe from a room.

    :param sid: Socket session ID
    :type sid: str
    :param room: Room to unsubscribe from
    :type room: str
    """
    await sio.leave_room(sid, room)
