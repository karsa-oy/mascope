"""Socket.IO session management."""

from typing import Dict, Any
from mascope_backend.socket.server import sio
from mascope_backend.db.models import User
from mascope_backend.socket.auth.exceptions import SocketSessionError
from mascope_backend.runtime import runtime


async def save_user_session(sid: str, user: User, namespace: str = "/") -> None:
    """
    Save authenticated user data to the Socket.IO session.

    Updates an existing session or creates a new one if none exists.

    :param sid: Socket.IO session ID.
    :type sid: str
    :param user: Authenticated user instance.
    :type user: User
    :param namespace: Namespace of the session.
    :type namespace: str
    :raises SocketSessionError: If the session cannot be saved.
    """
    try:
        session = await sio.get_session(sid, namespace=namespace) or {}
        session.update(
            {"user_id": user.id, "username": user.username, "role_id": user.role_id}
        )
        await sio.save_session(sid, session, namespace=namespace)
    except Exception as e:
        runtime.logger.error(f"Failed to save user session for SID '{sid}': {str(e)}")
        raise SocketSessionError("Failed to save session") from e


async def clear_user_session(sid: str, namespace: str = "/") -> None:
    """
    Clear user-related data from session.

    :param sid: Socket.IO session ID.
    :type sid: str
    :param namespace: Namespace of the session.
    :type namespace: str
    """
    try:
        session = await sio.get_session(sid, namespace=namespace)
        if not session:
            runtime.logger.trace(f"No session found to clear for {sid}")
            return
        await sio.save_session(sid, {}, namespace=namespace)
        runtime.logger.trace(f"Successfully cleared session for {sid}")
    except Exception as e:
        runtime.logger.error(f"Failed to clear session for {sid}: {str(e)}")


async def get_session_user(sid: str, namespace: str = "/") -> Dict[str, Any]:
    """
    Get user data from socket session.

    :param sid: Socket session ID
    :type sid: str
    :param namespace: Namespase of the session
    :type namespace: str
    :return: User session data
    :rtype: Dict[str, Any]
    :raises SocketSessionError: If session is not found or invalid
    """
    try:
        session = await sio.get_session(sid, namespace=namespace)
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
