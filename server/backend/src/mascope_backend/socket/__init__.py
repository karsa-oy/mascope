"""Socket.IO server initialization and configuration."""

from mascope_backend.runtime import runtime
from .server import sio
from .emitter import event_emitter
from .auth import authenticate_socket_connection, SocketUnauthenticatedError


def init_socket():
    """Initialize Socket.IO server and register event handlers."""
    from . import events

    runtime.logger.info("Registering socketio event handlers")
    return sio
