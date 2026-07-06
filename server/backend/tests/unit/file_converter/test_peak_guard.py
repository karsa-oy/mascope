"""Tests for the peak-detection concurrency guard."""

from concurrent.futures import ThreadPoolExecutor

from mascope_backend.file_converter.peak_guard import PeakDetectionGuard


class TestPeakDetectionGuard:
    def test_acquire_then_release_allows_reacquire(self):
        guard = PeakDetectionGuard()

        ok, reason = guard.acquire("file_a")
        assert ok and reason is None

        guard.release("file_a")
        ok, reason = guard.acquire("file_a")
        assert ok and reason is None

    def test_duplicate_acquire_is_rejected_with_reason(self):
        guard = PeakDetectionGuard()
        assert guard.acquire("file_a") == (True, None)

        ok, reason = guard.acquire("file_a")

        assert not ok
        assert "file_a" in reason

    def test_files_are_guarded_independently(self):
        guard = PeakDetectionGuard()
        assert guard.acquire("file_a")[0]
        assert guard.acquire("file_b")[0]

    def test_release_of_unknown_file_is_harmless(self):
        guard = PeakDetectionGuard()
        guard.release("never_acquired")  # must not raise
        assert guard.acquire("never_acquired")[0]

    def test_concurrent_acquires_grant_exactly_one_slot(self):
        guard = PeakDetectionGuard()

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: guard.acquire("same_file")[0], range(50)))

        assert sum(results) == 1
