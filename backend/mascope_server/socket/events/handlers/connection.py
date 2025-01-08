from mascope_server.socket.server import sio
from mascope_server.socket.auth import authenticate_socket_connection
from mascope_server.socket.auth.exceptions import SocketUnauthenticatedError
from mascope_server.runtime import runtime


@sio.event
async def connect(sid, environ):
    """
    Handle new socket connections.

    Attempts authentication but accepts unauthenticated connections.
    Authentication will be enforced per-event using decorators.

    NOTE: Authentication on Connection looks like current Socket.IO best practice.
    The unathienticated connections may be rejected for security reasons.
    This approach provides early authentication validation, clear connection lifecycle.
    Socket.IO will automatically disconnect the client if an exception raised
    during the connect event.
    """
    try:
        await authenticate_socket_connection(sid=sid, environ=environ)
        runtime.logger.debug(f"Socket client {sid} connected.")
    except SocketUnauthenticatedError as e:
        runtime.logger.debug(
            f"Socket client {sid} connected without authentication: {str(e)}"
        )
    except Exception as e:
        runtime.logger.error(f"Unexpected error during socket connection: {str(e)}")


@sio.event
async def disconnect(sid):
    """Handle socket disconnections."""
    runtime.logger.debug(f"Client {sid} disconnected")
