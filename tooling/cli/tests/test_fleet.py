"""
Tests for `mascope fleet` (SSH wrappers over the Ansible inventory).

Hermetic: the inventory is a temp file selected via MASCOPE_FLEET_INVENTORY,
and `ssh` is never executed - subprocess.run is monkeypatched to record the
argv the command builds.
"""

import shlex
import subprocess

import pytest

from mascope_cli.cmd import fleet


INVENTORY = """
fleet:
  hosts:
    server1:
      ansible_host: "100.64.0.11"
    server2:
      ansible_host: "100.64.0.12"
      ansible_user: "special"
  vars:
    ansible_user: "deploy"
    ansible_ssh_private_key_file: ~/.ssh/test-key
"""


@pytest.fixture
def inventory(tmp_path, monkeypatch):
    path = tmp_path / "inventory.local.yml"
    path.write_text(INVENTORY, encoding="utf-8")
    monkeypatch.setenv("MASCOPE_FLEET_INVENTORY", str(path))
    return path


@pytest.fixture
def ssh_calls(monkeypatch):
    """Record subprocess.run argvs instead of executing ssh."""
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(fleet.subprocess, "run", fake_run)
    return calls


# --- fleet list -------------------------------------------------------------


def test_list_shows_inventory_hosts(inventory, ssh_calls, cli_runner):
    result = cli_runner.invoke(fleet.fleet_app, ["list"])

    assert result.exit_code == 0
    assert "server1" in result.output
    assert "100.64.0.12" in result.output
    assert "special" in result.output  # per-host override wins over group var
    assert ssh_calls == []  # list never shells out


def test_list_without_inventory_fails(tmp_path, monkeypatch, cli_runner):
    monkeypatch.setenv("MASCOPE_FLEET_INVENTORY", str(tmp_path / "missing.yml"))
    result = cli_runner.invoke(fleet.fleet_app, ["list"])

    assert result.exit_code == 1
    assert "No fleet inventory found" in result.output
    assert "missing.yml" in result.output


# --- fleet logs -------------------------------------------------------------


def test_logs_builds_ssh_command(inventory, ssh_calls, cli_runner):
    result = cli_runner.invoke(
        fleet.fleet_app,
        ["logs", "server1", "-l", "error", "--interval", "1 day", "--json"],
    )

    assert result.exit_code == 0
    assert len(ssh_calls) == 1
    argv = ssh_calls[0]
    assert argv[0] == "ssh"
    key_index = argv.index("-i")
    assert argv[key_index + 1].endswith("test-key")
    assert "deploy@100.64.0.11" in argv
    remote = argv[-1]
    # --prod injected, flags passed through, values quoted for POSIX sh
    assert remote.startswith("mascope logs query --prod")
    assert "-l error" in remote
    assert shlex.quote("1 day") in remote
    assert "--json" in remote


def test_logs_quotes_hostile_grep_patterns(inventory, ssh_calls, cli_runner):
    pattern = "o'clock; rm -rf /"
    result = cli_runner.invoke(fleet.fleet_app, ["logs", "server1", "-g", pattern])

    assert result.exit_code == 0
    remote = ssh_calls[0][-1]
    assert shlex.quote(pattern) in remote
    # the naked metacharacters never appear unquoted
    assert "; rm" not in remote.replace(shlex.quote(pattern), "")


def test_logs_respects_explicit_mode(inventory, ssh_calls, cli_runner):
    result = cli_runner.invoke(fleet.fleet_app, ["logs", "server2", "--dev"])

    assert result.exit_code == 0
    argv = ssh_calls[0]
    assert "special@100.64.0.12" in argv  # per-host user override
    assert "--prod" not in argv[-1]
    assert "--dev" in argv[-1]


def test_logs_unknown_host_lists_inventory(inventory, ssh_calls, cli_runner):
    result = cli_runner.invoke(fleet.fleet_app, ["logs", "nosuch"])

    assert result.exit_code == 1
    assert "Unknown fleet host" in result.output
    assert "server1" in result.output
    assert ssh_calls == []


def test_logs_propagates_remote_exit_code(inventory, monkeypatch, cli_runner):
    monkeypatch.setattr(
        fleet.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 3),
    )
    result = cli_runner.invoke(fleet.fleet_app, ["logs", "server1"])

    assert result.exit_code == 3


# --- inventory resolution ---------------------------------------------------


def test_inventory_falls_back_to_mascope_path(
    tmp_path, monkeypatch, ssh_calls, cli_runner
):
    """A worktree without a local inventory uses $MASCOPE_PATH's copy."""
    monkeypatch.delenv("MASCOPE_FLEET_INVENTORY", raising=False)
    # no inventory in the (real) checkout root is assumed; make the shared
    # home carry one and hide the checkout copy if a developer has it
    monkeypatch.setattr(fleet, "source_checkout", lambda: tmp_path / "worktree")
    home = tmp_path / "home"
    (home / "tooling" / "fleet").mkdir(parents=True)
    (home / fleet.INVENTORY_RELPATH).write_text(INVENTORY, encoding="utf-8")
    monkeypatch.setenv("MASCOPE_PATH", str(home))

    result = cli_runner.invoke(fleet.fleet_app, ["logs", "server1"])

    assert result.exit_code == 0
    assert len(ssh_calls) == 1
