from typing import TYPE_CHECKING
from mascope_server.file_converter.socket.session import FileContext
from mascope_server.runtime import runtime

if TYPE_CHECKING:
    from .client import FileConverterSocketClient


class SocketEventHandler:
    def __init__(self, client: "FileConverterSocketClient"):
        self.client = client
        self.register_events()

    def register_events(self):
        @self.client.sio.event(namespace="/file-converter")
        def connect():
            runtime.logger.info(f"Connected to mascope server at {self.client.url}")

        @self.client.sio.event(namespace="/file-converter")
        def disconnect():
            runtime.logger.info("Disconnected from mascope server")

        @self.client.sio.on("file_context", namespace="/file-converter")
        def on_file_context(data):
            context = FileContext(
                filename=data["filename"],
                user_id=data["user_id"],
                username=data["username"],
                role_id=data["role_id"],
                access_token=data["access_token"],
            )
            self.client.context_manager.register_file(context)
