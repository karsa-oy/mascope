"""
Tests for the `mascope prod update --check` command wiring.

Verifies that the preflight is guarded by a running Postgres container, that
its classification propagates to the process exit code, and — most importantly
— that `--check` never touches the running stack (no `docker compose`).
"""

import importlib

import pytest
import typer


# The prod package re-exports a `main` function that shadows the module of the
# same name, so import the module explicitly (as test_prod_compose does).
prod_main = importlib.import_module("mascope_cli.cmd.prod.main")


def _fake_plan(classification="migration-update"):
    return prod_main.preflight.UpdatePlan(
        target="v1.3.0",
        classification=classification,
        image_changed=True,
        migration_pending=classification == "migration-update",
        current_revision="000000aaaaaa",
        target_revision="abc123def456",
    )


def test_preflight_requires_running_postgres(monkeypatch):
    monkeypatch.setattr(prod_main, "is_container_running", lambda mode: False)

    with pytest.raises(typer.Exit) as excinfo:
        prod_main._preflight("v1.2.0", pull=False, as_json=False)

    assert excinfo.value.exit_code == prod_main.preflight.ERROR_EXIT_CODE


def test_preflight_exits_with_plan_code(monkeypatch):
    monkeypatch.setattr(prod_main, "is_container_running", lambda mode: True)
    monkeypatch.setattr(
        prod_main.preflight,
        "build_plan",
        lambda **kwargs: _fake_plan("migration-update"),
    )

    with pytest.raises(typer.Exit) as excinfo:
        prod_main._preflight("v1.3.0", pull=True, as_json=False)

    assert excinfo.value.exit_code == 20


def test_preflight_error_exits_error_code(monkeypatch):
    monkeypatch.setattr(prod_main, "is_container_running", lambda mode: True)

    def _boom(**kwargs):
        raise prod_main.preflight.PreflightError("pull failed")

    monkeypatch.setattr(prod_main.preflight, "build_plan", _boom)

    with pytest.raises(typer.Exit) as excinfo:
        prod_main._preflight("v1.3.0", pull=True, as_json=False)

    assert excinfo.value.exit_code == prod_main.preflight.ERROR_EXIT_CODE


def test_update_check_does_not_apply(monkeypatch, cli_runner):
    """--check must classify and exit without running any docker compose."""
    monkeypatch.setattr(prod_main, "is_container_running", lambda mode: True)
    monkeypatch.setattr(
        prod_main.preflight, "build_plan", lambda **kwargs: _fake_plan("fast-update")
    )

    def _fail(*args, **kwargs):
        raise AssertionError("docker compose must not run under --check")

    monkeypatch.setattr(prod_main, "_run_compose", _fail)
    monkeypatch.setattr(prod_main, "check_data_dirs", _fail)

    result = cli_runner.invoke(prod_main.prod_app, ["update", "--check", "--no-pull"])

    assert result.exit_code == 10


def test_update_check_json_output(monkeypatch, cli_runner):
    monkeypatch.setattr(prod_main, "is_container_running", lambda mode: True)
    monkeypatch.setattr(
        prod_main.preflight,
        "build_plan",
        lambda **kwargs: _fake_plan("migration-update"),
    )
    monkeypatch.setattr(prod_main, "_run_compose", lambda *a, **k: None)

    result = cli_runner.invoke(
        prod_main.prod_app, ["update", "--check", "--no-pull", "--json"]
    )

    assert result.exit_code == 20
    assert '"classification": "migration-update"' in result.stdout
