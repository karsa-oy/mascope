"""Socket.IO server initialization and configuration."""

from mascope_server.runtime import runtime
from .server import sio
from .emitter import event_emitter
from .auth import authenticate_socket_connection, SocketUnauthenticatedError
from . import events


def init_socket():
    """Initialize Socket.IO server and register event handlers."""
    runtime.logger.info("Registering socketio event handlers")
    return sio
