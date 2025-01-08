import socketio
from mascope_server.socket.logging import get_socket_logger

# Main Socket.IO server instance
sio = socketio.AsyncServer(
    async_mode="asgi",  # run in ASGI mode
    cors_allowed_origins="*",  # allow all origins
    ping_timeout=60,
    logger=get_socket_logger(),
    engineio_logger=False,
)
