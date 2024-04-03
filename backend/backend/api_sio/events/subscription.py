from .. import sio


@sio.event(namespace="/")
async def subscribe(sid, room):
    await sio.enter_room(sid, room)


@sio.event(namespace="/")
async def unsubscribe(sid, room):
    await sio.leave_room(sid, room)
