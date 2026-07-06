"""
Tests for production compose invocation error propagation.

CI builds release images via `mascope prod build` and relies on its exit
status; a swallowed docker compose failure means jobs continue against
stale or missing images.
"""

import importlib
import subprocess

import pytest
import typer

# The prod package re-exports a `main` function that shadows the module of
# the same name, so import the module explicitly.
prod_main = importlib.import_module("mascope_cli.cmd.prod.main")


@pytest.fixture
def compose_env(monkeypatch):
    """Stub out config resolution and the subprocess itself."""
    monkeypatch.setattr(
        prod_main,
        "_compose_env",
        lambda building=False: {"MASCOPE_DB_NAME": "db", "MASCOPE_TIMEZONE": "UTC"},
    )

    def set_result(returncode: int):
        monkeypatch.setattr(
            prod_main.lib,
            "run",
            lambda **kwargs: subprocess.CompletedProcess([], returncode),
        )

    return set_result


def test_compose_failure_propagates_exit_code(compose_env):
    compose_env(17)

    with pytest.raises(typer.Exit) as excinfo:
        prod_main._run_compose(["build"], building=True)

    assert excinfo.value.exit_code == 17


def test_compose_success_returns_normally(compose_env):
    compose_env(0)

    prod_main._run_compose(["build"], building=True)  # must not raise
