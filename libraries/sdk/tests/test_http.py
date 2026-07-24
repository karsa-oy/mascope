"""
Hermetic unit tests for the low-level HTTP helpers in ``mascope_sdk._http``.

Unlike ``test_contract.py`` these do not need a running stack: they mock
``requests.post`` and inspect the request that ``requests`` would actually put
on the wire.
"""

import json

import requests

from mascope_sdk import _http


def _fake_ok_response() -> requests.Response:
    """A minimal 200 response carrying an empty ``data`` envelope."""
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"data": null}'
    return response


def test_http_post_sends_json_content_type(monkeypatch):
    """POST bodies must go out as ``application/json``.

    Regression test for the bug where ``http_post`` sent
    ``data=json.dumps(body)`` without a Content-Type header. ``requests`` does
    not set ``application/json`` for a raw string body, so FastAPI received the
    body as opaque bytes and rejected it with a 422
    ``model_attributes_type`` error (e.g. on
    ``POST /api/samples/{id}/peaks/timeseries``).

    The request is reconstructed through ``requests``' own preparation so the
    assertion reflects what actually reaches the server, independent of how the
    header gets set.
    """
    captured = {}
    body = {"peak_id": "csgxj7ZPeeVWlpA960Bj"}

    def fake_post(url, **kwargs):
        prepared = requests.Request(
            "POST",
            url,
            headers=kwargs.get("headers"),
            data=kwargs.get("data"),
            json=kwargs.get("json"),
        ).prepare()
        captured["content_type"] = prepared.headers.get("Content-Type")
        captured["body"] = prepared.body
        return _fake_ok_response()

    monkeypatch.setattr(_http.requests, "post", fake_post)

    _http.http_post(
        url="http://testserver",
        path="samples/abc/peaks/timeseries",
        access_token="token",
        data=body,
    )

    assert captured["content_type"] == "application/json"
    # And the body is valid JSON that round-trips to the original dict.
    sent = captured["body"]
    if isinstance(sent, bytes):
        sent = sent.decode()
    assert json.loads(sent) == body


def test_http_post_preserves_auth_headers(monkeypatch):
    """The Authorization / service headers must survive alongside the JSON body."""
    captured = {}

    def fake_post(url, **kwargs):
        captured["headers"] = kwargs.get("headers") or {}
        return _fake_ok_response()

    monkeypatch.setattr(_http.requests, "post", fake_post)

    _http.http_post(
        url="http://testserver",
        path="samples/abc/peaks/timeseries",
        access_token="secret-token",
        data={"peak_id": "x"},
        service_name="mascope_sdk",
    )

    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["headers"]["X-Service-Name"] == "mascope_sdk"


def _fake_error_response(status_code: int, payload: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload).encode()
    return response


def test_extract_error_message_prefers_backend_error_field():
    """The backend's error shape is ``{"error": <human message>, "detail":
    {"error_id": ...}}``. Regression test for the bug where the opaque detail
    dict was returned instead of the human-readable message.
    """
    response = _fake_error_response(
        404,
        {
            "error": "Failed to Get Sample. Sample not found.",
            "detail": {"error_id": "a1b2c3"},
        },
    )

    message = _http._extract_error_message(response)

    assert message == "Failed to Get Sample. Sample not found."


def test_extract_error_message_falls_back_to_detail():
    """Plain FastAPI-style ``{"detail": ...}`` errors still resolve."""
    response = _fake_error_response(404, {"detail": "Not found"})

    assert _http._extract_error_message(response) == "Not found"
