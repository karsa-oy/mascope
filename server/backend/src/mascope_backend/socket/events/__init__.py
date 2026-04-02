"""Socket.IO event system initialization.

This module initializes both the Socket.IO event handlers for client-server
communication and the internal event emitters for server-side events.
"""


def init_events():
    """Initialize event handlers and emitters."""
    from . import emitters, handlers  # noqa: F401 - imported to trigger registration
