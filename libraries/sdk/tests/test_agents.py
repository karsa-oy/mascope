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
    ServerError,
)


def _fake_response(status_code: int, payload: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload).encode()
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
