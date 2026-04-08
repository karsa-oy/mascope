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
    is_blank_sample_file,
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

    def _emit_blank_sample_warning(
        self,
        filename: str,
        sample_file_id: str | None,
        process_id: str | None,
        auth: dict,
    ) -> None:
        """Emit a warning when manual peak detection is requested for a blank sample."""
        self.socket_client.emit(
            "peak_detection_warning",
            {
                "filename": filename,
                "sample_file_id": sample_file_id,
                "process_id": process_id,
                "message": "No peaks found.",
            },
            auth,
        )

    def _process_request(self, request: dict) -> None:
        """Process a single peak-detection request.

        :param request: Queue item with filename, credentials, etc.
        """
        filename = request.get("filename")
        access_token = request.get("access_token")

        if not isinstance(filename, str) or not filename:
            raise ValueError("Peak detection request is missing a valid filename")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError(
                f"Peak detection request for '{filename}' is missing a valid access token"
            )

        sample_file_id = request.get("sample_file_id")
        affected_sample_item_ids = request.get("affected_sample_item_ids", [])
        process_id = request.get("process_id")
        auth = {
            "access_token": access_token,
            "user_id": request.get("user_id"),
        }

        runtime.logger.info(
            f"PeakRecomputeWorker: processing peak detection for '{filename}'"
        )
        try:
            if is_blank_sample_file(filename, access_token):
                runtime.logger.info(
                    f"PeakRecomputeWorker: skipping peak detection for blank sample '{filename}'"
                )
                self._emit_blank_sample_warning(
                    filename=filename,
                    sample_file_id=sample_file_id,
                    process_id=process_id,
                    auth=auth,
                )
                return

            instrument_functions = fetch_instrument_functions(
                filename,
                access_token,
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
