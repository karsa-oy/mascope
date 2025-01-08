"""Socket.IO session management."""

from typing import Dict, Any
from mascope_server.socket.server import sio
from mascope_server.db.models import User
from mascope_server.socket.auth.exceptions import SocketSessionError
from mascope_server.runtime import runtime


async def save_user_session(sid: str, user: User) -> None:
    """
    Save authenticated user data to socket session.

    :param sid: Socket.IO session ID
    :type sid: str
    :param user: Authenticated user instance
    :type user: User
    """
    await sio.save_session(
        sid, {"user_id": user.id, "username": user.username, "role_id": user.role_id}
    )


async def clear_user_session(sid: str) -> None:
    """
    Clear user-related data from session.

    :param sid: Socket.IO session ID
    """
    try:
        await sio.save_session(sid, {})
    except Exception as e:
        runtime.logger.error(f"Failed to clear session for {sid}: {str(e)}")


async def get_session_user(sid: str) -> Dict[str, Any]:
    """
    Get user data from socket session.

    :param sid: Socket session ID
    :type sid: str
    :return: User session data
    :rtype: Dict[str, Any]
    :raises SocketSessionError: If session is not found or invalid
    """
    try:
        session = await sio.get_session(sid)
        if not session:
            raise SocketSessionError("No session found")

        role_id = session.get("role_id")
        if role_id is None:
            raise SocketSessionError("No role found in session")

        return session
    except Exception as e:
        if isinstance(e, SocketSessionError):
            raise
        raise SocketSessionError(f"Session error: {str(e)}") from e
