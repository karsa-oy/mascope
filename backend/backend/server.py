import socketio

from backend.db import run as run_db


sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_timeout=60,
    logger=True,
)
app = socketio.ASGIApp(
    sio,
    on_startup=run_db,
)
