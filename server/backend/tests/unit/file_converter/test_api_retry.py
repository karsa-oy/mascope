"""
Tests for the file converter's transient-failure retry (``api._request_with_retry``).

During an ingest burst the backend answers 503 once its connection pool's
``pool_timeout`` expires. A single failed call must not quarantine the raw
file - the converter retries transport errors and 5xx responses with backoff,
while client-class statuses (2xx-4xx) return immediately.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from mascope_backend.file_converter import api


def _response(status_code: int) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    return response


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch.object(api.time, "sleep") as sleep:
        yield sleep


def test_5xx_is_retried_until_success(_no_sleep):
    responses = [_response(503), _response(503), _response(201)]
    with patch.object(api.requests, "request", side_effect=responses) as request:
        result = api._request_with_retry("POST", "http://x/api/y")

    assert result.status_code == 201
    assert request.call_count == 3
    assert _no_sleep.call_count == 2


def test_client_status_returns_immediately(_no_sleep):
    with patch.object(api.requests, "request", return_value=_response(400)) as request:
        result = api._request_with_retry("POST", "http://x/api/y")

    assert result.status_code == 400
    assert request.call_count == 1
    _no_sleep.assert_not_called()


def test_persistent_5xx_returns_last_response():
    with (
        patch.object(api.time, "sleep"),
        patch.object(api.requests, "request", return_value=_response(503)) as request,
    ):
        result = api._request_with_retry("GET", "http://x/api/y")

    assert result.status_code == 503
    assert request.call_count == len(api._RETRY_BACKOFF_S) + 1


def test_persistent_transport_error_is_reraised():
    error = requests.exceptions.ConnectionError("refused")
    with (
        patch.object(api.time, "sleep"),
        patch.object(api.requests, "request", side_effect=error),
    ):
        with pytest.raises(requests.exceptions.ConnectionError):
            api._request_with_retry("GET", "http://x/api/y")


def test_transport_error_then_success_recovers(_no_sleep):
    side_effects = [requests.exceptions.ConnectionError("refused"), _response(200)]
    with patch.object(api.requests, "request", side_effect=side_effects):
        result = api._request_with_retry("GET", "http://x/api/y")

    assert result.status_code == 200


def test_default_timeout_exceeds_server_pool_patience():
    """Client timeout must outlast the server's 120s pool_timeout."""
    with patch.object(api.requests, "request", return_value=_response(200)) as request:
        api._request_with_retry("GET", "http://x/api/y")

    assert request.call_args.kwargs["timeout"] > 120
