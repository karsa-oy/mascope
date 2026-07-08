"""
Tests for the production db script runner's container-Python resolution.

The interpreter path differs between image builds (``/opt/uv/tools`` on current
images, ``/root/.local/share/uv/tools`` on legacy ones), so the runner probes
the container at runtime instead of hardcoding a path.
"""

import subprocess

from mascope_cli.cmd.prod.db import scripts


def _fake_run(returncode: int, stdout: str):
    """Return a subprocess.run stand-in yielding a fixed CompletedProcess."""

    def _run(cmd, capture_output=False, text=False, check=False):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, returncode, stdout, "")

    return _run


def test_resolves_first_existing_tool_python(monkeypatch):
    # The probe echoes the first candidate that exists in the container.
    monkeypatch.setattr(
        scripts.subprocess,
        "run",
        _fake_run(0, "/opt/uv/tools/mascope/bin/python\n"),
    )
    assert (
        scripts._resolve_container_python("mascope_prod_backend")
        == "/opt/uv/tools/mascope/bin/python"
    )


def test_resolves_path_fallback_interpreter(monkeypatch):
    # When no tool path exists, the probe falls back to a PATH python that can
    # import mascope_backend and prints its resolved location.
    monkeypatch.setattr(
        scripts.subprocess, "run", _fake_run(0, "/usr/local/bin/python\n")
    )
    assert (
        scripts._resolve_container_python("mascope_prod_backend")
        == "/usr/local/bin/python"
    )


def test_returns_none_when_no_interpreter_found(monkeypatch):
    # Probe exits non-zero (nothing found) -> None, so the caller errors clearly.
    monkeypatch.setattr(scripts.subprocess, "run", _fake_run(1, ""))
    assert scripts._resolve_container_python("mascope_prod_backend") is None


def test_uses_the_current_dockerfile_path_first():
    # Guard the ordering: current images (UV_TOOL_DIR=/opt/uv/tools) must be
    # preferred over the legacy /root location.
    assert scripts._PYTHON_CANDIDATES[0] == "/opt/uv/tools/mascope/bin/python"
    assert (
        "/root/.local/share/uv/tools/mascope/bin/python" in scripts._PYTHON_CANDIDATES
    )
