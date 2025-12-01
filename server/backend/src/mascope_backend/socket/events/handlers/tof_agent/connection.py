"""
Tof Agent service connection lifecycle
"""

import os
from mascope_backend.socket import sio
from mascope_backend.socket.auth import authenticate_socket_connection
from mascope_backend.socket.auth.exceptions import SocketUnauthenticatedError
from mascope_backend.socket.auth.session import clear_user_session
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
            f"Tof agent connected with sid {sid} [Worker {worker_pid}]"
        )
        return True

    except SocketUnauthenticatedError as e:
        runtime.logger.error(
            f"Tof agent authentication failed. {str(e) }[Worker {worker_pid}]"
        )
        return False
    except Exception as e:
        runtime.logger.error(
            f"Unexpected error in Tof agent connection: {str(e)} [Worker {worker_pid}]"
        )
        return False


@sio.event(namespace="/tof-agent")
async def disconnect(sid):
    """Handle socket disconnections on tof-agent namespace."""
    # Clean up the session on disconnect
    await clear_user_session(sid, namespace="/tof-agent")
    runtime.logger.debug(f"Tof agent disconnected: {sid}")
