import socketio

import mascope_runtime as runtime

logger = runtime.logger.service('backend')

# Configure socket.io server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_timeout=60,
    logger=logger,
)
