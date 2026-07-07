"""
Tests for `mascope test run` command construction.

The command only assembles pytest/npm invocations and delegates to
`lib.run`; asserting on the assembled command strings covers the
component/module routing table without running any actual suite.
"""

import os

import pytest

from mascope_cli.cmd import lib
from mascope_cli.main import app


@pytest.fixture
def recorded_runs(monkeypatch):
    """Capture lib.run calls issued by the test command."""
    calls = []

    def fake_run(command, cwd=None, **kwargs):
        calls.append({"command": command, "cwd": cwd})

    monkeypatch.setattr(lib, "run", fake_run)
    return calls


def _commands(calls):
    return [c["command"] for c in calls]


def test_default_runs_backend_and_libraries(cli_runner, recorded_runs):
    result = cli_runner.invoke(app, ["test", "run"])

    assert result.exit_code == 0
    commands = _commands(recorded_runs)
    assert "pytest server/backend/tests/" in commands
    assert "pytest libraries/ --doctest-modules" in commands


def test_backend_module_scopes_the_path(cli_runner, recorded_runs):
    result = cli_runner.invoke(app, ["test", "run", "-m", "unit"])

    assert result.exit_code == 0
    assert _commands(recorded_runs) == ["pytest server/backend/tests/unit/"]


def test_library_module_routes_to_libraries(cli_runner, recorded_runs):
    result = cli_runner.invoke(app, ["test", "run", "-m", "sdk"])

    assert result.exit_code == 0
    assert _commands(recorded_runs) == ["pytest libraries/sdk/ --doctest-modules"]


def test_verbose_flag_is_forwarded(cli_runner, recorded_runs):
    result = cli_runner.invoke(app, ["test", "run", "backend", "-v"])

    assert result.exit_code == 0
    assert _commands(recorded_runs) == ["pytest server/backend/tests/ -v"]


def test_frontend_runs_vitest_in_frontend_dir(cli_runner, recorded_runs):
    result = cli_runner.invoke(app, ["test", "run", "frontend"])

    assert result.exit_code == 0
    npm = "npm.cmd" if os.name == "nt" else "npm"
    assert _commands(recorded_runs) == [f"{npm} run test:unit"]
    assert recorded_runs[0]["cwd"] == os.path.join("server", "frontend")
