"""
Tests for the filestream watcher (``file_converter/watcher.py``).

The watcher's job is to queue a file exactly once, and only after it has
stopped growing - queueing a half-written raw file corrupts ingestion.
"""

from queue import Queue
from threading import Event

import pytest

from mascope_backend.file_converter.watcher import FSWatcher


def make_watcher(tmp_path) -> FSWatcher:
    return FSWatcher(
        path=str(tmp_path),
        pattern="*.raw",
        file_queue=Queue(),
        shutdown_event=Event(),
    )


class TestWalk:
    def test_finds_matching_files_case_insensitively(self, tmp_path):
        (tmp_path / "a.raw").write_bytes(b"x")
        (tmp_path / "b.RAW").write_bytes(b"x")
        (tmp_path / "ignored.txt").write_bytes(b"x")

        watcher = make_watcher(tmp_path)

        found = {f.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for f in watcher.walk()}
        assert found == {"a.raw", "b.RAW"}

    def test_missing_directory_is_rejected(self, tmp_path):
        with pytest.raises(AssertionError, match="missing"):
            FSWatcher(
                path=str(tmp_path / "nope"),
                pattern="*.raw",
                file_queue=Queue(),
                shutdown_event=Event(),
            )


class TestOnCreated:
    def test_stable_file_is_queued_once(self, tmp_path):
        target = tmp_path / "sample.raw"
        target.write_bytes(b"12345")
        watcher = make_watcher(tmp_path)

        # First pass records the size (initial sentinel -1 != real size).
        in_progress = watcher.on_created([[str(target), -1]])
        assert in_progress == [[str(target), 5]]
        assert watcher.file_queue.empty()

        # Size unchanged on the second pass: the file is ready and queued.
        in_progress = watcher.on_created(in_progress)
        assert in_progress == []
        assert watcher.file_queue.get_nowait() == str(target)

    def test_growing_file_is_not_queued(self, tmp_path):
        target = tmp_path / "sample.raw"
        target.write_bytes(b"12345")
        watcher = make_watcher(tmp_path)

        in_progress = watcher.on_created([[str(target), -1]])
        target.write_bytes(b"1234567890")  # still being written

        in_progress = watcher.on_created(in_progress)

        assert in_progress == [[str(target), 10]]
        assert watcher.file_queue.empty()

    def test_deleted_file_is_dropped(self, tmp_path):
        target = tmp_path / "sample.raw"
        target.write_bytes(b"12345")
        watcher = make_watcher(tmp_path)
        in_progress = watcher.on_created([[str(target), -1]])

        target.unlink()

        assert watcher.on_created(in_progress) == []
        assert watcher.file_queue.empty()
