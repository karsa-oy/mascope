import socketio

from .socket import sio
from .fast import fast

from mascope_server.api.events.subscription import *
from mascope_server.api.events.instrument import *

sio_app = socketio.ASGIApp(socketio_server=sio, other_asgi_app=fast)
