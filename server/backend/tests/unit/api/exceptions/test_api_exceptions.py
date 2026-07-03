"""
Unit tests for API exception processing.

Focus: error responses must never leak internal details to clients.
Tracebacks and raw messages of unexpected exceptions stay in the server
logs, correlated to the response through an opaque ``error_id``.
"""

import json

import pytest

from mascope_backend.api.lib.exceptions.api_exceptions import (
    ApiException,
    api_e_response_json,
    handle_exception,
    process_exception,
)


def _raise_and_process(exc: Exception, context: str = "Test context") -> ApiException:
    """Process an exception from inside an except block, as production code does."""
    try:
        raise exc
    except Exception as e:
        return process_exception(e, context)


class TestProcessExceptionDoesNotLeakInternals:
    def test_unexpected_exception_detail_is_opaque(self):
        secret_path = "/app/.runtime/env/data/temp/secret-file"
        api_exc = _raise_and_process(FileNotFoundError(2, "No such file", secret_path))

        serialized = json.dumps(api_exc.tech_message)
        assert "traceback" not in serialized.lower()
        assert secret_path not in serialized
        assert set(api_exc.tech_message) == {"error_id"}
        assert len(api_exc.tech_message["error_id"]) == 32

    def test_unexpected_exception_user_message_is_generic(self):
        secret_path = "/app/.runtime/env/data/temp/secret-file"
        api_exc = _raise_and_process(FileNotFoundError(2, "No such file", secret_path))

        assert api_exc.status_code == 500
        assert secret_path not in api_exc.user_message
        assert api_exc.user_message == "Test context. Unexpected error."

    def test_response_json_contains_no_traceback(self):
        try:
            raise KeyError("internal_column_name")
        except Exception as e:
            response = handle_exception(e, "Test context")

        body = json.loads(response.body)
        assert response.status_code == 500
        assert "traceback" not in json.dumps(body).lower()
        assert list(body["detail"]) == ["error_id"]

    def test_api_exception_payload_is_preserved(self):
        payload = {"skipped_items": ["a", "b"]}
        api_exc = _raise_and_process(
            ApiException("Partial success", payload, status_code=207)
        )

        assert api_exc.status_code == 207
        assert api_exc.user_message == "Partial success"
        assert api_exc.tech_message["skipped_items"] == ["a", "b"]
        assert "error_id" in api_exc.tech_message
        assert "traceback" not in api_exc.tech_message

    def test_value_error_keeps_validation_message(self):
        api_exc = _raise_and_process(ValueError("mz must be positive"))

        assert api_exc.status_code == 400
        assert "mz must be positive" in api_exc.user_message
        assert set(api_exc.tech_message) == {"error_id"}


class TestApiEResponseJson:
    def test_detail_field_carries_tech_message(self):
        exc = ApiException("User message", {"error_id": "abc123"}, status_code=500)
        response = api_e_response_json(exc)

        body = json.loads(response.body)
        assert body == {"error": "User message", "detail": {"error_id": "abc123"}}


@pytest.mark.parametrize(
    "exc, expected_status",
    [
        (RuntimeError("boom"), 500),
        (ValueError("bad value"), 400),
        (AttributeError("missing attr"), 400),
    ],
)
def test_status_codes_and_opaque_detail(exc, expected_status):
    api_exc = _raise_and_process(exc)
    assert api_exc.status_code == expected_status
    assert set(api_exc.tech_message) == {"error_id"}
