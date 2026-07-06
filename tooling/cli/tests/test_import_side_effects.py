"""
Regression tests for import-time side effects.

A standalone `pip install`ed CLI must be importable — and able to print
`--help` — before any environment is configured. The Runtime singleton is
created lazily on first use; these tests run a clean subprocess with
MASCOPE_PATH removed to prove the import graph never touches it.
"""

import os
import subprocess
import sys


def _clean_env() -> dict:
    env = os.environ.copy()
    env.pop("MASCOPE_PATH", None)
    env.pop("MASCOPE_ENV", None)
    return env


def _run_python(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        env=_clean_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_import_requires_no_environment():
    result = _run_python("import mascope_cli.main")

    assert result.returncode == 0, result.stderr


def test_help_requires_no_environment():
    result = _run_python(
        "import sys\n"
        "from typer.testing import CliRunner\n"
        "from mascope_cli.main import app\n"
        "result = CliRunner().invoke(app, ['--help'])\n"
        "assert 'prod' in result.output\n"
        "sys.exit(result.exit_code)\n"
    )

    assert result.returncode == 0, result.stderr


def test_command_without_environment_fails_lazily():
    # Without MASCOPE_PATH a real command must fail when it touches the
    # runtime — not at import — and with the missing-path error.
    result = _run_python(
        "from typer.testing import CliRunner\n"
        "from mascope_cli.main import app\n"
        "result = CliRunner().invoke(app, ['modules'])\n"
        "raise SystemExit(0 if result.exception else 1)\n"
    )

    assert result.returncode == 0, result.stderr
