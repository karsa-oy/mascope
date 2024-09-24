from mascope_server.runtime import runtime

from mascope_server.app.socket import sio

runtime.logger.info("Registering socketio subscription event handlers")


@sio.event(namespace="/")
async def subscribe(sid, room):
    await sio.enter_room(sid, room)


@sio.event(namespace="/")
async def unsubscribe(sid, room):
    await sio.leave_room(sid, room)
