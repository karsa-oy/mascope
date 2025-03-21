"""Socket.IO ASGI application initialization."""

import socketio
from mascope_backend.socket import init_socket
from mascope_backend.socket.events import init_events
from .fast import fast


def create_socket_app():
    """Create and initialize the Socket.IO ASGI application."""
    # Initialize socket and events
    sio = init_socket()
    init_events()

    # Create ASGI app
    return socketio.ASGIApp(socketio_server=sio, other_asgi_app=fast)


# Create the application instance
sio_app = create_socket_app()
