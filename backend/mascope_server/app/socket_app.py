import socketio
from mascope_server.socket import init_socket
from .fast import fast


sio = init_socket()
sio_app = socketio.ASGIApp(socketio_server=sio, other_asgi_app=fast)
