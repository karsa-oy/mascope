from hardware.tofwerk.lib.TwTool import *

# these 3 imports require loaded library from TwTool
import backend.api.calibration
import backend.api.instrument
import backend.api.match
import backend.api.sample
import backend.api.scenthound
import backend.api.schema
import backend.api.target
import backend.api.template
import backend.api.visualization
from backend.server import sio


@sio.event(namespace="/")
async def subscribe(sid, room):
    sio.enter_room(sid, room)


@sio.event(namespace="/")
async def unsubscribe(sid, room):
    sio.leave_room(sid, room)
