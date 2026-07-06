"""
Tests for the top-level `mascope` entrypoint.

The `--help` and utility-command tests double as an import-graph smoke test:
invoking the app registers every sub-app (dev, prod, demo, env, ...), so any
circular-import or import-time regression in the command tree fails here
before it fails in someone's terminal.

The callback tests pin down the version/env-var contract that `mascope prod`
deploys rely on (MASCOPE_VERSION pinning, log level/grep propagation).
"""

import os

from mascope_cli.main import app


def test_help_lists_full_command_tree(cli_runner):
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("env", "demo", "dev", "prod", "logs", "backend", "test"):
        assert command in result.output


def test_modules_lists_known_modules(cli_runner):
    result = cli_runner.invoke(app, ["modules"])
    assert result.exit_code == 0
    assert "backend" in result.output
    assert "frontend" in result.output


def test_groups_lists_tags(cli_runner, monkeypatch):
    # Rich falls back to an 80-column table in tests and truncates cells;
    # widen the virtual terminal so tag names survive intact.
    monkeypatch.setenv("COLUMNS", "200")
    result = cli_runner.invoke(app, ["groups"])
    assert result.exit_code == 0
    assert "server" in result.output


def test_path_prints_mascope_home(cli_runner, mascope_home):
    result = cli_runner.invoke(app, ["path"])
    assert result.exit_code == 0
    assert str(mascope_home) in result.output


def test_version_derived_from_git_when_unpinned(cli_runner):
    assert "MASCOPE_VERSION" not in os.environ
    result = cli_runner.invoke(app, ["path"])
    assert result.exit_code == 0
    # The callback derives a version and records that it was not pinned.
    assert os.environ["_MASCOPE_VERSION_PINNED"] == "0"
    assert os.environ["MASCOPE_VERSION"]


def test_explicit_version_pin_is_honored(cli_runner, monkeypatch):
    monkeypatch.setenv("MASCOPE_VERSION", "v9.9.9")
    result = cli_runner.invoke(app, ["path"])
    assert result.exit_code == 0
    assert os.environ["_MASCOPE_VERSION_PINNED"] == "1"
    assert os.environ["MASCOPE_VERSION"] == "v9.9.9"


def test_log_level_option_sets_env_var(cli_runner):
    result = cli_runner.invoke(app, ["--log-level", "debug", "path"])
    assert result.exit_code == 0
    assert os.environ["MASCOPE_LOGLEVEL"] == "DEBUG"


def test_stale_log_level_is_cleared(cli_runner, monkeypatch):
    # A previous invocation's env var must not leak into docker compose.
    monkeypatch.setenv("MASCOPE_LOGLEVEL", "TRACE")
    result = cli_runner.invoke(app, ["path"])
    assert result.exit_code == 0
    assert "MASCOPE_LOGLEVEL" not in os.environ


def test_log_grep_option_sets_env_var(cli_runner):
    result = cli_runner.invoke(app, ["--log-grep", "some-pattern", "path"])
    assert result.exit_code == 0
    assert os.environ["MASCOPE_LOGGREP"] == "some-pattern"


def test_stale_log_grep_is_cleared(cli_runner, monkeypatch):
    monkeypatch.setenv("MASCOPE_LOGGREP", "old-pattern")
    result = cli_runner.invoke(app, ["path"])
    assert result.exit_code == 0
    assert "MASCOPE_LOGGREP" not in os.environ
