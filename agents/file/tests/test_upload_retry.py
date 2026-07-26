"""Unit tests for the upload retry policy in main.process_file_upload.

Hermetic: the upload call and runtime are monkeypatched; no sleeping, no
network.
"""

import pytest

from mascope_file_agent import main
from mascope_sdk.exceptions import (
    AuthenticationError,
    MascopeConnectionError,
    NotFoundError,
    ValidationError,
)


class StubLogger:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        pass

    def info(self, message):
        pass

    def debug(self, message):
        pass


class StubConfig:
    def __init__(self, source):
        self.source = source


class StubRuntime:
    def __init__(self, source):
        self.logger = StubLogger()
        self.config = StubConfig(source)


@pytest.fixture
def stub_runtime(monkeypatch, tmp_path):
    runtime = StubRuntime(str(tmp_path))
    monkeypatch.setattr(main, "runtime", runtime)
    monkeypatch.setattr(main.time, "sleep", lambda seconds: None)
    return runtime


def _failing_upload(monkeypatch, exception):
    calls = []

    def fail(filepath):
        calls.append(filepath)
        raise exception

    monkeypatch.setattr(main, "upload_sample_file", fail)
    return calls


@pytest.mark.parametrize(
    "exception",
    [
        NotFoundError("Not found.", status_code=404, url="http://x/api/upload"),
        ValidationError("Invalid.", status_code=422),
        AuthenticationError("Rejected.", status_code=401),
    ],
)
def test_no_retry_on_client_errors(stub_runtime, monkeypatch, tmp_path, exception):
    calls = _failing_upload(monkeypatch, exception)
    sample = tmp_path / "x.raw"
    sample.write_text("data")

    main.process_file_upload(str(sample))

    assert len(calls) == 1  # failed fast, no retries
    assert (tmp_path / "failed_uploads" / "x.raw").exists()
    assert any("Retrying will not help" in e for e in stub_runtime.logger.errors)


def test_retries_on_connection_errors(stub_runtime, monkeypatch, tmp_path):
    calls = _failing_upload(monkeypatch, MascopeConnectionError("refused"))
    sample = tmp_path / "x.raw"
    sample.write_text("data")

    main.process_file_upload(str(sample), max_retries=3)

    assert len(calls) == 3  # transient errors keep retrying to the cap
    assert (tmp_path / "failed_uploads" / "x.raw").exists()
