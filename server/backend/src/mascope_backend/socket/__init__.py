"""Socket.IO server initialization and configuration."""

from mascope_backend.runtime import runtime

from .emitter import event_emitter as event_emitter
from .server import sio


def init_socket():
    """Initialize Socket.IO server and register event handlers."""
    from . import events  # noqa: F401 - imported to trigger registration

    runtime.logger.info("Registering socketio event handlers")
    return sio
