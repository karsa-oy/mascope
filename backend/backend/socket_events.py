import socketio

# Configure socket.io server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_timeout=60,
    logger=True,
)


@sio.event(namespace="/")
async def subscribe(sid, room):
    sio.enter_room(sid, room)


@sio.event(namespace="/")
async def unsubscribe(sid, room):
    sio.leave_room(sid, room)
