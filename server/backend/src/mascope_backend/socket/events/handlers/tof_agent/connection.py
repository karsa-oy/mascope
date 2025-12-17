"""
TOF-Agent service connection lifecycle.

Handles socket connections on the /tof-agent namespace used by the TOF instrument service.
"""

import os
from mascope_backend.socket import sio
from mascope_backend.socket.auth import authenticate_socket_connection
from mascope_backend.socket.auth.exceptions import (
    SocketUnauthenticatedError,
)
from mascope_backend.socket.storage import (
    clear_user_session,
    get_session_user,
    room_tracker,
    SocketSessionError,
)
from mascope_backend.runtime import runtime


@sio.event(namespace="/tof-agent")
async def connect(sid: str, environ: dict, auth: dict) -> bool:
    """
    Handle Tof agent service connections.

    Authenticates the connection using the access token provided in the auth parameter
    and associates the connection with the authenticated user's session.
    Returns False to refuse connection or True to accept it.

    :param sid: Socket session ID
    :type sid: str
    :param environ: WSGI environment containing request data
    :type environ: dict
    :param auth: Authentication data containing access_token
    :type auth: dict
    :return: Connection acceptance status
    :rtype: bool
    """
    worker_pid = os.getpid()
    try:
        # Step 1: Verify tof-agent connection
        service_name = environ.get("HTTP_X_SERVICE_NAME")
        if service_name != "tof-agent":
            raise SocketUnauthenticatedError(
                f"Unexpected connection to tof-agent namespace: {service_name} [Worker {worker_pid}]"
            )

        # Step 2: Extract access token
        access_token = auth.get("access_token")
        if not access_token:
            raise SocketUnauthenticatedError("No access token provided")

        # Step 3: Authenticate connection
        await authenticate_socket_connection(
            sid=sid, token=access_token, minimum_role="editor", service_name="tof-agent"
        )
        runtime.logger.debug(
            f"TOF-Agent connected with sid {sid} [Worker {worker_pid}]"
        )
        return True

    except SocketUnauthenticatedError as e:
        runtime.logger.error(
            f"TOF-Agent authentication failed. {str(e) } [Worker {worker_pid}]"
        )
        return False
    except Exception as e:
        runtime.logger.error(
            f"Unexpected error in TOF-Agent connection: {str(e)} [Worker {worker_pid}]"
        )
        return False


@sio.event(namespace="/tof-agent")
async def disconnect(sid):
    """
    Handle socket disconnections on tof-agent namespace.
    - Remove user from all room memberships (room_tracker)
    - Clear authentication session (session manager)

    :param sid: Socket session ID
    :type sid: str
    """
    runtime.logger.debug(f"TOF-Agent disconnecting: {sid}")

    try:
        # Clean up room memberships
        session = await get_session_user(sid, namespace="/tof-agent")
        user_id = session["user_id"]
        await room_tracker.leave_all(user_id)

        runtime.logger.debug(
            f"TOF-Agent disconnected: cleaned up rooms for user {user_id} (sid={sid})"
        )

    except SocketSessionError:
        runtime.logger.trace(f"TOF-Agent disconnect: no session found for {sid}")

    finally:
        # Clear authentication session
        await clear_user_session(sid, namespace="/tof-agent")
