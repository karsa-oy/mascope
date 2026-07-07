"""
Regression tests for import-time side effects and the no-checkout flow.

A standalone `pip install`ed CLI must be importable — and able to print
`--help` — before any environment is configured, fail commands with guidance
rather than a crash, and become fully functional after `mascope init`. These
tests run clean subprocesses with MASCOPE_PATH removed and the platform
default home redirected into a temp directory, so a real home on the
developer's machine never leaks in.
"""

import os
import subprocess
import sys


def _clean_env(home_base) -> dict:
    env = os.environ.copy()
    env.pop("MASCOPE_PATH", None)
    env.pop("MASCOPE_ENV", None)
    # Redirect the platform default home (LOCALAPPDATA on Windows, ~ elsewhere)
    # so tests never see or touch a real initialized home.
    env["LOCALAPPDATA"] = str(home_base)
    env["USERPROFILE"] = str(home_base)
    env["HOME"] = str(home_base)
    return env


def _run_python(code: str, home_base) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        env=_clean_env(home_base),
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_import_requires_no_environment(tmp_path):
    result = _run_python("import mascope_cli.main", tmp_path)

    assert result.returncode == 0, result.stderr


def test_help_requires_no_environment(tmp_path):
    result = _run_python(
        "import sys\n"
        "from typer.testing import CliRunner\n"
        "from mascope_cli.main import app\n"
        "result = CliRunner().invoke(app, ['--help'])\n"
        "assert 'prod' in result.output\n"
        "sys.exit(result.exit_code)\n",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr


def test_command_without_home_fails_with_guidance(tmp_path):
    # Without MASCOPE_PATH or an initialized home, a real command must fail
    # lazily (not at import) and point the user at `mascope init`.
    result = _run_python(
        "from typer.testing import CliRunner\n"
        "from mascope_cli.main import app\n"
        "result = CliRunner().invoke(app, ['modules'])\n"
        "assert result.exit_code != 0, 'expected failure without a home'\n"
        "try:\n"
        "    stderr = result.stderr\n"
        "except ValueError:\n"
        "    stderr = ''  # stderr mixed into output on this click version\n"
        "output = result.output + stderr\n"
        "assert 'mascope init' in output, output\n",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr + result.stdout


def test_init_makes_commands_work_without_mascope_path(tmp_path):
    # The pip-install UX in one process: `mascope init` (no env at all),
    # then a runtime-backed command resolves the freshly created default home.
    result = _run_python(
        "import sys\n"
        "from typer.testing import CliRunner\n"
        "from mascope_cli.main import app\n"
        "runner = CliRunner()\n"
        "init = runner.invoke(app, ['init'])\n"
        "assert init.exit_code == 0, init.output\n"
        "modules = runner.invoke(app, ['modules'])\n"
        "assert modules.exit_code == 0, modules.output\n"
        "assert 'backend' in modules.output\n",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr + result.stdout
