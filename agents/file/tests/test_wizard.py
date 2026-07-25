"""Unit tests for the File Agent setup wizard.

Hermetic: prompts and HTTP calls are monkeypatched.
"""

import pytest

from mascope_file_agent import wizard


class FakeResponse:
    def __init__(self, status_code, content_type="application/json"):
        self.status_code = status_code
        self.headers = {"content-type": content_type}


def test_verify_connection_accepts_200_json(monkeypatch):
    captured = {}

    def fake_get(url, params, headers, verify, timeout):
        captured.update(url=url, headers=headers)
        return FakeResponse(200)

    monkeypatch.setattr(wizard.requests, "get", fake_get)
    ok, message = wizard.verify_connection("mascope.example.com", "tok")
    assert ok and message == ""
    assert captured["url"] == "https://mascope.example.com/api/sample/files"
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert captured["headers"]["X-Service-Name"] == "file-agent"


def test_verify_connection_rejects_html_200(monkeypatch):
    # A single-page-app server (e.g. the Vite frontend dev server) answers
    # any GET with the app page and 200; that must not pass verification.
    monkeypatch.setattr(
        wizard.requests,
        "get",
        lambda *a, **k: FakeResponse(200, content_type="text/html; charset=utf-8"),
    )
    ok, message = wizard.verify_connection("localhost:5173", "tok")
    assert not ok
    assert "does not look like the Mascope API" in message
    assert "http://localhost:8090" in message


@pytest.mark.parametrize("status", [401, 403])
def test_verify_connection_rejected_token(monkeypatch, status):
    monkeypatch.setattr(wizard.requests, "get", lambda *a, **k: FakeResponse(status))
    ok, message = wizard.verify_connection("mascope.example.com", "bad")
    assert not ok
    assert "rejected the access token" in message


def test_verify_connection_unreachable(monkeypatch):
    def fake_get(*args, **kwargs):
        raise wizard.requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(wizard.requests, "get", fake_get)
    ok, message = wizard.verify_connection("mascope.example.com", "tok")
    assert not ok
    assert "Could not connect" in message


def test_run_setup_wizard_happy_path(monkeypatch, tmp_path, capsys):
    source = tmp_path / "watched"
    source.mkdir()
    answers = iter(
        [
            "https://mascope.example.com/",  # server address (normalized)
            "my-token",  # access token
            str(source),  # watched folder
            "",  # mask: accept default
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(wizard, "verify_connection", lambda host, token: (True, ""))

    settings = wizard.run_setup_wizard({"mask": "*.raw", "timeout": 3})

    assert settings["host"] == "mascope.example.com"
    assert settings["access_token"] == "my-token"
    assert settings["source"] == str(source)
    assert settings["mask"] == "*.raw"
    assert settings["timeout"] == 3
    assert "accepted the access token" in capsys.readouterr().out


def test_run_setup_wizard_retries_bad_token(monkeypatch, tmp_path):
    source = tmp_path / "watched"
    source.mkdir()
    answers = iter(
        [
            "mascope.example.com",  # server address
            "bad-token",  # first token attempt
            "t",  # choose: re-enter token
            "good-token",  # second token attempt
            str(source),  # watched folder
            "",  # mask default
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(
        wizard,
        "verify_connection",
        lambda host, token: (token == "good-token", "The server rejected the token."),
    )

    settings = wizard.run_setup_wizard({"mask": "*.raw", "timeout": 3})
    assert settings["access_token"] == "good-token"


def test_run_setup_wizard_creates_missing_source(monkeypatch, tmp_path):
    source = tmp_path / "new-folder"
    answers = iter(
        [
            "mascope.example.com",
            "tok",
            str(source),  # does not exist yet
            "y",  # create it
            "",  # mask default
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(wizard, "verify_connection", lambda host, token: (True, ""))

    settings = wizard.run_setup_wizard({"mask": "*.raw", "timeout": 3})
    assert settings["source"] == str(source)
    assert source.is_dir()
