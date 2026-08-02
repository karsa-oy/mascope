"""
Tests for the converter's startup wait (``service.wait_for_backend``).

The converter starts alongside the backend, so connection refusals during
startup are routine: they must be retried quietly (no ERROR-level records,
which the monitoring sink would forward to GlitchTip) and escalate to a
single WARNING only when the backend stays unreachable well past a normal
startup.
"""

from unittest.mock import MagicMock, patch

import pytest

from mascope_backend.file_converter import service


@pytest.fixture()
def shutdown_event():
    """A SHUTDOWN_EVENT stand-in that never sleeps and is never set."""
    event = MagicMock()
    event.is_set.return_value = False
    event.wait.return_value = False
    with patch.object(service, "SHUTDOWN_EVENT", event):
        yield event


@pytest.fixture()
def logger():
    # runtime.logger is a read-only property; swap the module's runtime
    # reference so the logger calls land on a plain mock.
    fake_runtime = MagicMock()
    with patch.object(service, "runtime", fake_runtime):
        yield fake_runtime.logger


def test_retries_quietly_until_connected(shutdown_event, logger):
    client = MagicMock()
    client.connect.side_effect = [Exception("refused"), Exception("refused"), None]

    with patch.object(service, "SOCKET_CLIENT", client):
        assert service.wait_for_backend() is True

    assert client.connect.call_count == 3
    # Startup refusals are routine: INFO only, nothing the monitoring
    # sink (WARNING+) would forward to GlitchTip.
    logger.error.assert_not_called()
    logger.exception.assert_not_called()
    logger.warning.assert_not_called()


def test_backoff_delays_double_up_to_the_cap(shutdown_event, logger):
    client = MagicMock()
    client.connect.side_effect = [Exception("refused")] * 8 + [None]

    with patch.object(service, "SOCKET_CLIENT", client):
        assert service.wait_for_backend() is True

    delays = [call.args[0] for call in shutdown_event.wait.call_args_list]
    assert delays == [1, 2, 4, 8, 16, 30, 30, 30]


def test_warns_once_when_the_wait_stops_looking_like_a_startup(
    shutdown_event, logger, monkeypatch
):
    monkeypatch.setattr(service, "CONNECT_WARN_AFTER_S", 3)
    client = MagicMock()
    client.connect.side_effect = [Exception("refused")] * 5 + [None]

    with patch.object(service, "SOCKET_CLIENT", client):
        assert service.wait_for_backend() is True

    # One WARNING (= one monitored event), not one per attempt
    assert logger.warning.call_count == 1
    logger.error.assert_not_called()


def test_returns_false_on_shutdown_without_connecting(logger):
    event = MagicMock()
    event.is_set.return_value = True
    client = MagicMock()

    with (
        patch.object(service, "SHUTDOWN_EVENT", event),
        patch.object(service, "SOCKET_CLIENT", client),
    ):
        assert service.wait_for_backend() is False

    client.connect.assert_not_called()
