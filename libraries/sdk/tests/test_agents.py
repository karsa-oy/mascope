"""Hermetic unit tests for the agent upload helper in ``mascope_sdk._agents``.

Regression tests for the bug where ``api_post_file`` logged the specific
failure cause (rejected token, connection error, server message) but returned
``None``, leaving callers with nothing better than a generic "upload failed".
"""

import json

import pytest
import requests

from mascope_sdk import _agents
from mascope_sdk.exceptions import (
    AuthenticationError,
    MascopeConnectionError,
    NotFoundError,
    ServerError,
    ValidationError,
)


def _fake_response(
    status_code: int, payload: dict | None = None, headers: dict | None = None
) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload or {}).encode()
    if headers:
        response.headers.update(headers)
    return response


@pytest.fixture
def upload_file(tmp_path):
    path = tmp_path / "sample.raw"
    path.write_bytes(b"raw-bytes")
    return str(path)


def test_rejected_token_raises_authentication_error(monkeypatch, upload_file):
    monkeypatch.setattr(
        _agents.requests,
        "post",
        lambda *a, **k: _fake_response(
            401, {"error": "Authorization failed. Please sign in to the Mascope."}
        ),
    )

    with pytest.raises(AuthenticationError) as exc_info:
        _agents.api_post_file(
            "http://testserver", "sample/files/upload", "bad", upload_file
        )

    # The server's message and the token hint both reach the caller.
    assert "Authorization failed" in str(exc_info.value)
    assert "API token" in str(exc_info.value)


def test_server_error_carries_backend_message(monkeypatch, upload_file):
    monkeypatch.setattr(
        _agents.requests,
        "post",
        lambda *a, **k: _fake_response(
            500,
            {"error": "Failed to process sample file.", "detail": {"error_id": "x"}},
        ),
    )

    with pytest.raises(ServerError) as exc_info:
        _agents.api_post_file(
            "http://testserver", "sample/files/upload", "t", upload_file
        )

    assert "Failed to process sample file." in str(exc_info.value)


def test_connection_failure_raises_connection_error(monkeypatch, upload_file):
    def fake_post(*a, **k):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(_agents.requests, "post", fake_post)

    with pytest.raises(MascopeConnectionError):
        _agents.api_post_file(
            "http://testserver", "sample/files/upload", "t", upload_file
        )


def test_success_returns_response(monkeypatch, upload_file):
    monkeypatch.setattr(
        _agents.requests,
        "post",
        lambda *a, **k: _fake_response(201, {"message": "uploaded"}),
    )

    resp = _agents.api_post_file(
        "http://testserver", "sample/files/upload", "t", upload_file
    )

    assert resp.status_code == 201


# --- api_post_file_tus ---


TUS_LOCATION = {"Location": "http://proxy.internal/api/sample/files/upload/tus/abc123"}


def _fake_create(captured: dict):
    def fake_post(url, headers, verify, timeout):
        captured.update(url=url, headers=headers)
        return _fake_response(201, headers=TUS_LOCATION)

    return fake_post


def test_tus_upload_chunks_whole_file(monkeypatch, upload_file):
    created: dict = {}
    chunks: list[tuple[str, bytes]] = []

    def fake_patch(url, data, headers, verify, timeout):
        chunks.append((headers["Upload-Offset"], bytes(data)))
        return _fake_response(204)

    monkeypatch.setattr(_agents.requests, "post", _fake_create(created))
    monkeypatch.setattr(_agents.requests, "patch", fake_patch)

    _agents.api_post_file_tus("http://testserver", "tok", upload_file, chunk_size=4)

    # created against our own base URL, with the TUS protocol headers
    assert created["url"] == "http://testserver/api/sample/files/upload/tus/"
    assert created["headers"]["Authorization"] == "Bearer tok"
    assert created["headers"]["Tus-Resumable"] == "1.0.0"
    assert created["headers"]["Upload-Length"] == "9"  # len(b"raw-bytes")
    assert created["headers"]["Upload-Metadata"].startswith("filename ")
    # the 9-byte file went out in 4-byte chunks with advancing offsets
    assert [offset for offset, _ in chunks] == ["0", "4", "8"]
    assert b"".join(data for _, data in chunks) == b"raw-bytes"


def test_tus_upload_addresses_chunks_via_own_base_url(monkeypatch, upload_file):
    # The Location header points at whatever host/scheme the proxy chain
    # reported; only the upload id may be trusted.
    urls: list[str] = []

    def fake_patch(url, data, headers, verify, timeout):
        urls.append(url)
        return _fake_response(204)

    monkeypatch.setattr(_agents.requests, "post", _fake_create({}))
    monkeypatch.setattr(_agents.requests, "patch", fake_patch)

    _agents.api_post_file_tus("http://testserver", "tok", upload_file)

    assert urls == ["http://testserver/api/sample/files/upload/tus/abc123"]


def test_tus_upload_resumes_from_server_offset(monkeypatch, upload_file):
    monkeypatch.setattr(_agents.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(_agents.requests, "post", _fake_create({}))
    monkeypatch.setattr(
        _agents.requests,
        "head",
        lambda *a, **k: _fake_response(200, headers={"Upload-Offset": "3"}),
    )
    attempts = {"n": 0}
    chunks: list[tuple[str, bytes]] = []

    def fake_patch(url, data, headers, verify, timeout):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise requests.exceptions.ConnectionError("dropped mid-chunk")
        chunks.append((headers["Upload-Offset"], bytes(data)))
        return _fake_response(204)

    monkeypatch.setattr(_agents.requests, "patch", fake_patch)

    _agents.api_post_file_tus("http://testserver", "tok", upload_file)

    # resumed from the server-confirmed offset, not from zero
    assert chunks == [("3", b"raw-bytes"[3:])]


def test_tus_upload_gives_up_after_max_attempts(monkeypatch, upload_file):
    monkeypatch.setattr(_agents.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(_agents.requests, "post", _fake_create({}))
    monkeypatch.setattr(_agents.requests, "head", lambda *a, **k: _fake_response(404))
    attempts = {"n": 0}

    def fake_patch(*args, **kwargs):
        attempts["n"] += 1
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(_agents.requests, "patch", fake_patch)

    with pytest.raises(MascopeConnectionError):
        _agents.api_post_file_tus("http://testserver", "tok", upload_file)

    assert attempts["n"] == _agents.TUS_MAX_ATTEMPTS


def test_tus_upload_does_not_retry_client_errors(monkeypatch, upload_file):
    monkeypatch.setattr(_agents.requests, "post", _fake_create({}))
    attempts = {"n": 0}

    def fake_patch(*args, **kwargs):
        attempts["n"] += 1
        return _fake_response(422, {"error": "Invalid."})

    monkeypatch.setattr(_agents.requests, "patch", fake_patch)

    with pytest.raises(ValidationError):
        _agents.api_post_file_tus("http://testserver", "tok", upload_file)

    assert attempts["n"] == 1  # a rejected request cannot heal by waiting


@pytest.mark.parametrize(
    ("status", "exception"),
    [(404, NotFoundError), (401, AuthenticationError)],
)
def test_tus_create_failure_is_typed_for_fallback(
    monkeypatch, upload_file, status, exception
):
    # The File Agent falls back to the legacy endpoint on these: a 404
    # means no TUS route (old server), a 401 means the route is not
    # token-accessible (old server) or a genuinely bad token.
    monkeypatch.setattr(
        _agents.requests, "post", lambda *a, **k: _fake_response(status)
    )
    with pytest.raises(exception):
        _agents.api_post_file_tus("http://testserver", "tok", upload_file)


def test_tus_upload_empty_file_completes_at_creation(monkeypatch, tmp_path):
    empty = tmp_path / "empty.raw"
    empty.write_bytes(b"")
    monkeypatch.setattr(_agents.requests, "post", _fake_create({}))
    monkeypatch.setattr(
        _agents.requests,
        "patch",
        lambda *a, **k: pytest.fail("no PATCH expected for an empty file"),
    )

    _agents.api_post_file_tus("http://testserver", "tok", str(empty))


def test_tus_upload_rejects_filename_with_path(monkeypatch, upload_file):
    with pytest.raises(ValueError, match="path components"):
        _agents.api_post_file_tus(
            "http://testserver", "tok", upload_file, upload_filename="a/b.raw"
        )
