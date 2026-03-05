"""
Worker threads that handle peak detection requests from the backend.

When a user manually triggers peak detection from the UI, the backend
emits a peak_detection_request Socket.IO event.
The file converter socket handler enqueues the request, and PeakRecomputeWorker
threads process it.

Multiple worker threads share a single Queue and run concurrently.
The CPU-heavy fitting work is off-loaded to a ProcessPoolExecutor
inside detect_peaks.

PeakDetectionGuard rejects duplicate requests for the same sample file
at enqueue time (in the socket event handler), so the workers only see
unique filenames.
"""

import traceback
from queue import Empty, Queue
from threading import Event, Thread

from mascope_backend.file_converter.api import (
    fetch_instrument_functions,
    rematch_sample,
)
from mascope_backend.file_converter.peak_guard import PeakDetectionGuard
from mascope_backend.file_converter.runtime import runtime
from mascope_signal.peak import compute_peaks


class PeakRecomputeWorker(Thread):
    """Worker thread that pulls peak detection requests from a shared queue.

    Multiple instances can run in parallel for concurrent processing.

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

    def _process_request(self, request: dict) -> None:
        """Process a single peak-detection request.

        :param request: Queue item with filename, credentials, etc.
        """
        filename = request.get("filename")
        sample_file_id = request.get("sample_file_id")
        affected_sample_item_ids = request.get("affected_sample_item_ids", [])
        process_id = request.get("process_id")
        auth = {
            "access_token": request.get("access_token"),
            "user_id": request.get("user_id"),
        }

        runtime.logger.info(
            f"PeakRecomputeWorker: processing peak detection for '{filename}'"
        )
        try:
            instrument_functions = fetch_instrument_functions(
                filename,
                request.get("access_token"),
            )

            def progress_callback(progress: int):
                self.socket_client.emit(
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

            if affected_sample_item_ids:
                for sample_item_id in affected_sample_item_ids:
                    rematch_sample(
                        sample_item_id=sample_item_id,
                        access_token=auth["access_token"],
                        full_remove=True,
                    )

            runtime.logger.info(
                f"PeakRecomputeWorker: peak detection complete for '{filename}'"
            )

            self.socket_client.emit(
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
                f"PeakRecomputeWorker: peak detection failed for '{filename}': "
                f"{e}\n{traceback.format_exc()}"
            )
            self.socket_client.emit(
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

    def run(self) -> None:
        """Thread entry point: pull requests from the queue and process them."""
        runtime.logger.info("PeakRecomputeWorker started")
        while not self.shutdown_event.is_set():
            try:
                request = self.queue.get(timeout=1)
            except Empty:
                continue
            self._process_request(request)
        runtime.logger.info("PeakRecomputeWorker stopped")
