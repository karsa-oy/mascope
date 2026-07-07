"""
Packaging smoke test for the standalone mascope-cli wheel.

Run inside an isolated environment where the built mascope_cli wheel (and its
mascope_runtime dependency) are installed and the platform default home is
redirected to a throwaway directory, e.g.:

    uv build --package mascope_cli --out-dir dist
    uv build --package mascope_runtime --out-dir dist
    HOME=$(mktemp -d) uv run --isolated --no-project \
        --with dist/mascope_cli-*.whl --find-links dist \
        python .github/scripts/wheel_smoke.py

Asserts the operator install contract: no source checkout detected, no
developer commands or dependencies, and the fresh-machine flow
(`mascope init` -> a runtime-backed command) works end to end.
"""

import importlib.util

from typer.testing import CliRunner

from mascope_cli.checkout import source_checkout
from mascope_cli.main import app


# A wheel install must not look like a source checkout.
assert source_checkout() is None, f"unexpected checkout: {source_checkout()}"

# Dev-only dependencies must not be present in the operator install.
for module in ("alembic", "psycopg2", "pandas"):
    assert importlib.util.find_spec(module) is None, f"{module} leaked in"

runner = CliRunner()

result = runner.invoke(app, ["--help"])
assert result.exit_code == 0, result.output
for command in ("init", "prod", "env", "demo", "logs", "cert"):
    assert command in result.output, f"operator command {command} missing"

# Developer commands must not be registered.
for command in ("dev", "test", "agent", "backend"):
    probe = runner.invoke(app, [command, "--help"])
    assert probe.exit_code != 0, f"developer command {command} is registered"

# The fresh-machine flow: init the default home, then run a command that
# needs the runtime (config loading, state, version resolution).
init = runner.invoke(app, ["init"])
assert init.exit_code == 0, init.output

modules = runner.invoke(app, ["modules"])
assert modules.exit_code == 0, modules.output
assert "backend" in modules.output

print("wheel smoke OK: operator surface only, dev deps absent, init flow works")
