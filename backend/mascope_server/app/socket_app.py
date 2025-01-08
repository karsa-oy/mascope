import socketio
from mascope_server.socket import sio
from .fast import fast

sio_app = socketio.ASGIApp(socketio_server=sio, other_asgi_app=fast)
