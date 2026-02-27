from typing import TYPE_CHECKING

from mascope_backend.file_converter.socket.session import FileContext
from mascope_backend.runtime import runtime


if TYPE_CHECKING:
    from queue import Queue
    from .client import FileConverterSocketClient


class SocketEventHandler:
    def __init__(
        self,
        client: "FileConverterSocketClient",
        peak_recompute_queue: "Queue | None" = None,
    ):
        self.client = client
        self._peak_recompute_queue = peak_recompute_queue
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
            context = _build_file_context(data)
            self.client.context_manager.register_file(context)

        @self.client.sio.on("peak_detection_request", namespace="/file-converter")
        def on_peak_detection_request(data):
            """Handles peak detection requests from the backend.

            Registers a temporary file context for authentication, then
            enqueues the request for the PeakRecomputeWorker thread.

            Authentication is required since peak detection needs to fetch instrument
            functions via HTTP as the file converter has no DB access.
            """
            runtime.logger.info(
                f"Received peak detection request for {data['filename']}"
            )
            context = _build_file_context(data)
            self.client.context_manager.register_file(context)

            if self._peak_recompute_queue is not None:
                self._peak_recompute_queue.put(data)
            else:
                runtime.logger.error(
                    "Peak detection queue not available - ignoring request"
                )


def _build_file_context(data: dict) -> FileContext:
    """Helper to build FileContext from incoming socket data"""
    return FileContext(
        filename=data["filename"],
        user_id=data["user_id"],
        username=data["username"],
        role_id=data["role_id"],
        access_token=data["access_token"],
    )
