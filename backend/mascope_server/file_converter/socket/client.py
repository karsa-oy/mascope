import socketio
from mascope_server.file_converter.socket.session import FileContextManager
from mascope_server.file_converter.socket.events import SocketEventHandler
from mascope_server.runtime import runtime


class FileConverterSocketClient:
    """Socket.IO client for file converter service"""

    def __init__(self, url: str):
        self.url = url
        self.sio = socketio.Client(logger=False, ssl_verify=False)
        self.context_manager = FileContextManager()
        self.event_handler = SocketEventHandler(self)
        self._print_registered_events()

    def _print_registered_events(self):
        """Print all registered event handlers in a single line"""
        all_events = [
            f"{event}"
            for namespace in self.sio.handlers.values()
            for event in namespace.keys()
        ]
        runtime.logger.debug(
            f"Registered socket events: {', '.join(sorted(set(all_events)))}"
        )

    def connect(self):
        """Connect to Mascope server"""
        try:
            self.sio.connect(
                self.url,
                headers={"X-Service-Name": "file-converter"},
                namespaces=["/file-converter"],
            )
        except Exception as e:
            runtime.logger.error(f"Failed to connect: {str(e)}")
            raise

    def emit(self, event: str, data: dict):
        """Emit event with user context if available"""
        try:
            # Add user context if available
            if "filename" in data:
                context = self.context_manager.get_context(data["filename"])
                if context:
                    data.update(
                        {
                            "access_token": context.access_token,
                        }
                    )
            self.sio.emit(event, data, namespace="/file-converter")
        except Exception as e:
            runtime.logger.error(f"Failed to emit {event}: {str(e)}")
