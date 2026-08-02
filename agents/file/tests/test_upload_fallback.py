"""Unit tests for the TUS-first upload path and its legacy fallback.

Hermetic: the SDK upload functions and the runtime are monkeypatched.
"""

import pytest

from mascope_file_agent import main
from mascope_sdk.exceptions import NotFoundError, TusNotSupportedError


class StubLogger:
    def error(self, message):
        pass

    def warning(self, message):
        pass

    def info(self, message):
        pass

    def debug(self, message):
        pass


class StubConfig:
    mask = "*.raw"
    access_token = "tok"
    filename_prefix = ""
    filename_suffix = ""


class StubRuntime:
    def __init__(self):
        self.logger = StubLogger()
        self.config = StubConfig()


@pytest.fixture
def sample_file(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "runtime", StubRuntime())
    monkeypatch.setattr(main, "URL", "https://mascope.example.com")
    monkeypatch.setattr(main, "_legacy_upload", False)
    sample = tmp_path / "x.raw"
    sample.write_bytes(b"data")
    return str(sample)


def test_uploads_via_tus_by_default(monkeypatch, sample_file):
    tus_calls = []
    monkeypatch.setattr(
        main, "api_post_file_tus", lambda **kwargs: tus_calls.append(kwargs)
    )
    monkeypatch.setattr(
        main,
        "api_post_file",
        lambda **kwargs: pytest.fail("legacy endpoint must not be used"),
    )

    main.upload_sample_file(sample_file)

    assert len(tus_calls) == 1
    assert tus_calls[0]["filepath"] == sample_file
    assert not main._legacy_upload


@pytest.mark.parametrize("status", [404, 401])
def test_falls_back_to_legacy_endpoint_on_old_server(monkeypatch, sample_file, status):
    tus_calls = []
    legacy_calls = []

    def failing_tus(**kwargs):
        tus_calls.append(kwargs)
        raise TusNotSupportedError("No token TUS access.", status_code=status)

    monkeypatch.setattr(main, "api_post_file_tus", failing_tus)
    monkeypatch.setattr(
        main, "api_post_file", lambda **kwargs: legacy_calls.append(kwargs)
    )

    main.upload_sample_file(sample_file)
    assert len(legacy_calls) == 1
    assert main._legacy_upload

    # subsequent uploads skip the doomed TUS attempt entirely
    main.upload_sample_file(sample_file)
    assert len(tus_calls) == 1
    assert len(legacy_calls) == 2


def test_mid_transfer_errors_do_not_latch_legacy_fallback(monkeypatch, sample_file):
    # An upload vanishing mid-transfer (e.g. backend restart) keeps its
    # normal type: the outer retry loop handles it, and the agent must
    # not conclude "old server" and cap itself at 100 MB.
    def failing_tus(**kwargs):
        raise NotFoundError("Upload not found", status_code=404)

    monkeypatch.setattr(main, "api_post_file_tus", failing_tus)
    monkeypatch.setattr(
        main,
        "api_post_file",
        lambda **kwargs: pytest.fail("legacy endpoint must not be used"),
    )

    with pytest.raises(NotFoundError):
        main.upload_sample_file(sample_file)

    assert not main._legacy_upload


def test_legacy_fallback_enforces_size_cap(monkeypatch, sample_file):
    def failing_tus(**kwargs):
        raise TusNotSupportedError("No token TUS access.", status_code=404)

    monkeypatch.setattr(main, "api_post_file_tus", failing_tus)
    monkeypatch.setattr(
        main,
        "api_post_file",
        lambda **kwargs: pytest.fail("an oversized file must not be uploaded"),
    )
    monkeypatch.setattr(main, "FILE_UPLOAD_SIZE_LIMIT", 2)  # sample is 4 bytes

    with pytest.raises(ValueError, match="exceeds the maximum"):
        main.upload_sample_file(sample_file)


def test_tus_uploads_have_no_size_cap(monkeypatch, sample_file):
    tus_calls = []
    monkeypatch.setattr(
        main, "api_post_file_tus", lambda **kwargs: tus_calls.append(kwargs)
    )
    monkeypatch.setattr(main, "FILE_UPLOAD_SIZE_LIMIT", 2)  # sample is 4 bytes

    main.upload_sample_file(sample_file)

    assert len(tus_calls) == 1


def test_rejects_extension_not_matching_mask(monkeypatch, tmp_path, sample_file):
    wrong = tmp_path / "x.txt"
    wrong.write_bytes(b"data")

    with pytest.raises(ValueError, match="not an allowed file extension"):
        main.upload_sample_file(str(wrong))
