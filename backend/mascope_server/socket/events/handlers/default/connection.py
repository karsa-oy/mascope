"""
Frontend user connection lifecycle for Mascope web application.

Handles socket connections on the default namespace used by the main web application.
"""

from mascope_server.socket.server import sio
from mascope_server.socket.auth import authenticate_socket_connection
from mascope_server.socket.auth.token import get_jwt_from_cookies
from mascope_server.socket.auth.session import clear_user_session
from mascope_server.socket.auth.exceptions import SocketUnauthenticatedError
from mascope_server.runtime import runtime


@sio.event(namespace="/")
async def connect(sid: str, environ: dict) -> bool:
    """
    Handle new frontend user connections on default namespace.

    Attempts authentication from the JWT token in cookies. Returns True to accept
    the connection or False to refuse it.

    NOTE: Authentication on connection looks like current Socket.IO best practice.
    The unathienticated connections may be rejected for security reasons.
    This approach provides early authentication validation, clear connection lifecycle.
    Socket.IO will automatically disconnect the client if an exception raised
    during the connect or if event returned False.

    :param sid: Socket session ID
    :type sid: str
    :param environ: WSGI environment containing request data
    :type environ: dict
    :return: Connection acceptance status
    :rtype: bool
    """
    try:
        # Step 1: Get cookies from environment
        cookies = environ.get("HTTP_COOKIE")
        if not cookies:
            raise SocketUnauthenticatedError("No cookies in request")

        # Step 2: Extract JWT token
        jwt_token = await get_jwt_from_cookies(cookies)

        # Step 3: Authenticate socket connection and associate session with user
        await authenticate_socket_connection(
            sid=sid, token=jwt_token, minimum_role="guest"
        )
        runtime.logger.debug(f"User's socket client {sid} connected.")
        return True

    except SocketUnauthenticatedError as e:
        runtime.logger.error(f"User socket session authentication failed: {str(e)}")
        return False
    except Exception as e:
        runtime.logger.error(f"Unexpected errorduring user socket connection: {str(e)}")
        return False


@sio.event
async def disconnect(sid: str) -> None:
    """
    Handle frontend user socket disconnections.

    :param sid: Socket session ID
    :type sid: str
    """
    await clear_user_session(sid)
    runtime.logger.debug(f"User session disconnected: {sid}")
