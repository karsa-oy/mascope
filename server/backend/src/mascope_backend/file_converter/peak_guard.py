"""
Peak detection guard that prevents duplicate concurrent peak detection for the same file.
"""

import threading

from mascope_backend.file_converter.runtime import runtime


class PeakDetectionGuard:
    """Thread-safe guard that rejects duplicate peak detection requests.

    Usage::

        ok, reason = guard.acquire(filename)
        if not ok:
            # `reason` explains why (file already being processed)
            return
        try:
            do_peak_detection(filename)
        finally:
            guard.release(filename)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._files_in_progress: set[str] = set()

    def acquire(self, filename: str) -> tuple[bool, str | None]:
        """Mark sample file as in-progress.

        :param filename: Base filename of a sample file.
        :type: str
        :return: (True, None) on success, or (False, reason) if rejected.
        :rtype: tuple[bool, str | None]
        """
        with self._lock:
            if filename in self._files_in_progress:
                reason = (
                    f"Peak detection already in progress for '{filename}'. "
                    "Please wait for the current operation to complete."
                )
                runtime.logger.warning(reason)
                return False, reason
            self._files_in_progress.add(filename)

        runtime.logger.debug(f"Peak detection slot acquired for '{filename}'")
        return True, None

    def release(self, filename: str) -> None:
        """Release the peak detection slot for the sample file.

        :param filename: The sample file base filename for which to release the slot.
        :type filename: str
        """
        with self._lock:
            self._files_in_progress.discard(filename)
        runtime.logger.debug(f"Peak detection slot released for '{filename}'")
