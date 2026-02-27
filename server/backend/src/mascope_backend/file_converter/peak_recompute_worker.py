"""
Worker thread that handles peak detection requests from the backend.

When a user manually triggers peak detection from UI, the backend
emits a `peak_detection_request` Socket.IO event instead of computing
peaks itself. The file converter socket handler enqueues
the request, and this worker processes it. Global `PeakDetectionGuard`
ensures only one file is fitted at a time and rejects duplicate requests
for the same file.
"""

import asyncio
import traceback
from queue import Empty, Queue
from threading import Event, Thread

from mascope_backend.file_converter.api import fetch_instrument_functions
from mascope_backend.file_converter.peak_guard import PeakDetectionGuard
from mascope_backend.file_converter.runtime import runtime
from mascope_signal.peak import compute_peaks


class PeakRecomputeWorker(Thread):
    """Thread that serially processes delegated peak detection requests.

    :param socket_client: File converter socket client for emitting results.
    :param peak_recompute_queue: Thread-safe queue that receives request dicts.
    :param peak_guard: Shared guard for serialization / duplicate rejection.
    :param shutdown_event: Set to signal graceful shutdown.
    """

    def __init__(
        self,
        socket_client,
        peak_recompute_queue: Queue,
        peak_guard: PeakDetectionGuard,
        shutdown_event: Event,
    ):
        super().__init__(daemon=True, name="PeakRecomputeWorker")
        self.socket_client = socket_client
        self.queue = peak_recompute_queue
        self.peak_guard = peak_guard
        self.shutdown_event = shutdown_event

    def run(self):
        runtime.logger.info("PeakRecomputeWorker started")

        while not self.shutdown_event.is_set():
            try:
                peak_detection_request = self.queue.get(timeout=0.5)
            except Empty:
                continue

            filename = peak_detection_request.get("filename")
            sample_file_id = peak_detection_request.get("sample_file_id")

            runtime.logger.info(
                f"PeakRecomputeWorker: processing peak detection for '{filename}'"
            )

            is_acquired, failure_reason = self.peak_guard.acquire(filename)
            if not is_acquired:
                # Duplicate — emit warning back to backend
                self.socket_client.emit(
                    "peak_detection_error",
                    {
                        "filename": filename,
                        "sample_file_id": sample_file_id,
                        "error": failure_reason,
                    },
                )
                continue

            try:
                # Fetch instrument functions via HTTP (file converter has no DB access)
                auth_context = self.socket_client.context_manager.get_context(filename)
                if not auth_context:
                    raise RuntimeError(f"No auth context available for '{filename}'")
                instrument_functions = fetch_instrument_functions(
                    filename, auth_context.access_token
                )
                asyncio.run(compute_peaks(filename, instrument_functions))

                runtime.logger.info(
                    f"PeakRecomputeWorker: peak detection complete for '{filename}'"
                )
                self.socket_client.emit(
                    "peak_detection_complete",
                    {
                        "filename": filename,
                        "sample_file_id": sample_file_id,
                    },
                )

            except Exception as e:
                runtime.logger.error(
                    f"PeakRecomputeWorker: peak detection failed for '{filename}': "
                    f"{e}\n{traceback.format_exc()}"
                )
                self.socket_client.emit(
                    "peak_detection_error",
                    {
                        "filename": filename,
                        "sample_file_id": sample_file_id,
                        "error": str(e),
                    },
                )
            finally:
                self.peak_guard.release(filename)
                # Clear the temporary auth context registered for this request
                self.socket_client.context_manager.clear_context(filename)

        runtime.logger.info("PeakRecomputeWorker stopped")
