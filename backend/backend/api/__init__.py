from backend.lib.hardware.tofwerk.lib.TwTool import *

# these 3 imports require loaded library from TwTool
from backend.api.calibration import *
from backend.api.match import *
from backend.api.sample import *

from backend.api.schema import *
from backend.api.signal import *
from backend.api.target import *
from backend.api.template import *
from backend.api.visualization import *
from backend.api.workspace import *
from backend.server import sio

@sio.event(namespace='/')
async def subscribe(sid, room):
    sio.enter_room(sid, room)

@sio.event(namespace='/')
async def unsubscribe(sid, room):
    sio.leave_room(sid, room)