"""Socket.IO server initialization and configuration."""

from mascope_server.runtime import runtime
from .server import sio
from .emitter import event_emitter
from .auth import authenticate_socket_connection, SocketUnauthenticatedError
from . import events

runtime.logger.debug("Registering socketio event handlers")
