"""
Async event-loop thread that handles peak detection requests from the backend.

When a user manually triggers peak detection from UI, the backend
emits a peak_detection_request Socket.IO event.  The file converter
socket handler enqueues the request, and PeakRecomputeLoop processes it.

A an asyncio event loop runs inside a single daemon thread.
Each incoming request becomes an asyncio.Task so that multiple files
can be fitted concurrently (bound by an asyncio.Semaphore).  The
CPU-heavy fitting work is off-loaded to a global
ProcessPoolExecutor via run_in_executor inside detect_peaks.

PeakDetectionGuard rejects duplicate requests for the same sample file
at enqueue time (in the socket event handler), so the loop only sees
unique filenames.
"""

import asyncio
import functools
import traceback
from queue import Empty, Queue
from threading import Event, Thread

from mascope_backend.file_converter.api import fetch_instrument_functions
from mascope_backend.file_converter.peak_guard import PeakDetectionGuard
from mascope_backend.file_converter.runtime import runtime
from mascope_signal.peak import compute_peaks


class PeakRecomputeLoop(Thread):
    """Thread running a persistent asyncio loop for peak detection tasks.

    :param socket_client: File converter socket client for emitting results.
    :param peak_recompute_queue: Thread-safe queue that receives request dicts.
    :param peak_guard: Shared guard for serialization / duplicate rejection.
    :param shutdown_event: Set to signal graceful shutdown.
    :param max_concurrent: Maximum number of files processed in parallel.
    """

    def __init__(
        self,
        socket_client,
        peak_recompute_queue: Queue,
        peak_guard: PeakDetectionGuard,
        shutdown_event: Event,
        max_concurrent: int = 1,
    ):
        super().__init__(daemon=True, name="PeakRecomputeLoop")
        self.socket_client = socket_client
        self.queue = peak_recompute_queue
        self.peak_guard = peak_guard
        self.shutdown_event = shutdown_event
        self.max_concurrent = max_concurrent

    def _emit_with_auth(self, event: str, data: dict, auth: dict):
        """Emit a socket event with auth credentials payload.

        :param event: Socket.IO event name to emit
        :type event: str
        :param data: Event payload data (e.g. filename, progress, etc.)
        :type data: dict
        :param auth: Authentication credentials to include in the payload.
        :type auth: dict
        """
        payload = {**data, **auth}
        self.socket_client.sio.emit(event, payload, namespace="/file-converter")

    async def _process_request(
        self,
        request: dict,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Process a single peak-detection request under the semaphore.

        :param request: Queue item with filename, credentials, etc.
        :param semaphore: Concurrency limiter.
        """
        filename = request.get("filename")
        sample_file_id = request.get("sample_file_id")
        process_id = request.get("process_id")
        auth = {
            "access_token": request.get("access_token"),
            "user_id": request.get("user_id"),
        }

        async with semaphore:
            runtime.logger.info(
                f"PeakRecomputeLoop: processing peak detection for '{filename}'"
            )
            try:
                instrument_functions = fetch_instrument_functions(
                    filename,
                    request.get("access_token"),
                )

                def progress_callback(progress: int):
                    self._emit_with_auth(
                        "peak_detection_progress",
                        {
                            "filename": filename,
                            "sample_file_id": sample_file_id,
                            "process_id": process_id,
                            "progress": progress,
                        },
                        auth,
                    )

            compute_peaks(
                filename,
                instrument_functions,
                progress_callback=progress_callback,
            )

                runtime.logger.info(
                    f"PeakRecomputeLoop: peak detection complete for '{filename}'"
                )
                self._emit_with_auth(
                    "peak_detection_complete",
                    {
                        "filename": filename,
                        "sample_file_id": sample_file_id,
                        "process_id": process_id,
                    },
                    auth,
                )

            except Exception as e:
                runtime.logger.error(
                    f"PeakRecomputeLoop: peak detection failed for '{filename}': "
                    f"{e}\n{traceback.format_exc()}"
                )
                self._emit_with_auth(
                    "peak_detection_error",
                    {
                        "filename": filename,
                        "sample_file_id": sample_file_id,
                        "process_id": process_id,
                        "error": str(e),
                    },
                    auth,
                )
            finally:
                self.peak_guard.release(filename)

    async def _run_loop(self) -> None:
        """Main loop that continuously processes incoming peak detection requests."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        loop = asyncio.get_running_loop()

        while not self.shutdown_event.is_set():
            # Non-blocking queue poll with timeout to allow periodic shutdown checks.
            try:
                request = await loop.run_in_executor(
                    None,
                    functools.partial(self.queue.get, timeout=0.5),
                )
            except Empty:
                continue

            # Each request is processed in its own asyncio.Task so that multiple files
            # can be processed concurrently (up to the semaphore limit).
            asyncio.create_task(
                self._process_request(request, semaphore),
                name=f"peak-detect-{request.get('filename', '?')}",
            )

    def run(self) -> None:
        """Thread entry point, starts the asyncio event loop."""
        runtime.logger.info(
            f"PeakRecomputeLoop started (max_concurrent={self.max_concurrent})"
        )
        asyncio.run(self._run_loop())
        runtime.logger.info("PeakRecomputeLoop stopped")
