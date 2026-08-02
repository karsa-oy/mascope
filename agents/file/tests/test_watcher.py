"""Unit tests for the watcher wiring and failed_uploads exclusion in main.

Hermetic: the runtime is stubbed and sleeps are patched out; no observer
threads are started.
"""

from queue import Empty

import pytest

from mascope_file_agent import main


class StubLogger:
    def error(self, message):
        pass

    def warning(self, message):
        pass

    def info(self, message):
        pass

    def debug(self, message):
        pass


class StubRuntime:
    def __init__(self):
        self.logger = StubLogger()


@pytest.fixture
def stub_runtime(monkeypatch):
    runtime = StubRuntime()
    monkeypatch.setattr(main, "runtime", runtime)
    monkeypatch.setattr(main.time, "sleep", lambda seconds: None)
    return runtime


def test_recursive_flag_reaches_the_watcher(stub_runtime, tmp_path):
    uploader = main.FileUploader(str(tmp_path), "*.raw", recursive=True)
    assert uploader.watcher.recursive is True
    # and the default stays non-recursive
    assert main.FileUploader(str(tmp_path), "*.raw").watcher.recursive is False


def test_file_in_subfolder_is_queued(stub_runtime, tmp_path):
    uploader = main.FileUploader(str(tmp_path), "*.raw", recursive=True)
    sample = tmp_path / "day1" / "x.raw"
    sample.parent.mkdir()
    sample.write_text("data")

    uploader.on_filesystem_object_created(str(sample))

    assert uploader.jobs.get(timeout=5) == str(sample)


def test_file_in_failed_uploads_is_ignored(stub_runtime, tmp_path):
    # failed_uploads holds copies of files that already failed; picking
    # them up under recursive watching would loop them forever
    uploader = main.FileUploader(str(tmp_path), "*.raw", recursive=True)
    failed = tmp_path / "failed_uploads" / "x.raw"
    failed.parent.mkdir()
    failed.write_text("data")

    uploader.on_filesystem_object_created(str(failed))

    with pytest.raises(Empty):
        uploader.jobs.get(timeout=0.2)
