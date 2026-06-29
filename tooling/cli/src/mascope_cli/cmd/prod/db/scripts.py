"""
Production database script runner.

Discovers and executes maintenance scripts from
`mascope_backend.db.scripts.*` inside the production backend container,
with automatic pre-execution backup.

Scripts are data-manipulation entry points — see `mascope_backend.db.admin`
for the distinction from Alembic schema migrations.
"""

import importlib
import importlib.util
import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from mascope_cli.pg import check_prerequisites, dirs, pg_dump
from mascope_cli.runtime import runtime


prod_db_scripts_app = typer.Typer()

_MODE = "prod"
_SCRIPTS_MODULE = "mascope_backend.db.scripts"
_PYTHON = "/root/.local/share/uv/tools/mascope/bin/python"

# Environment variables forwarded from the host into the backend container
# when running scripts via `docker exec -e`.
_FORWARDED_ENV_VARS = ["MIN_DATETIME", "UTC_OFFSET_HOURS", "ALLOW_MATCHED_LOSS"]


def _discover_scripts() -> dict[str, str]:
    """
    Discover available scripts from mascope_backend.db.scripts.

    :return: Mapping of CLI name to dotted module path.
    :rtype: dict[str, str]
    """
    spec = importlib.util.find_spec(_SCRIPTS_MODULE)
    if spec is None or spec.submodule_search_locations is None:
        return {}

    scripts_dir = Path(next(iter(spec.submodule_search_locations)))
    result = {}

    for path in sorted(scripts_dir.glob("*.py")):
        if path.stem == "__init__":
            continue
        module_path = f"{_SCRIPTS_MODULE}.{path.stem}"
        try:
            mod = importlib.import_module(module_path)
            if callable(getattr(mod, "main", None)):
                cli_name = path.stem
                result[cli_name] = module_path
        except Exception:
            pass

    return result


@prod_db_scripts_app.callback()
def main() -> None:
    """
    Run data maintenance scripts against the production database.

    Scripts manipulate existing data — they do not change the schema.
    For schema changes, the db-init container runs Alembic on startup.

    A backup is always taken before execution.
    """


@prod_db_scripts_app.command("list")
def list_scripts() -> None:
    """List available maintenance scripts."""
    scripts = _discover_scripts()
    if not scripts:
        runtime.logger.warning("No scripts found in mascope_backend.db.scripts")
        return
    runtime.logger.info("Available scripts:")
    for name, module in scripts.items():
        runtime.logger.info(f"  {name}")


@prod_db_scripts_app.command("run")
def run_script(
    script: Annotated[
        str,
        typer.Argument(help="Script name. Run 'list' to see available scripts."),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm execution against prod."),
    ] = False,
    skip_backup: Annotated[
        bool,
        typer.Option(
            "--skip-backup",
            "-S",
            help="Skip the pre-execution backup. Use for large databases "
            "where pg_dump is prohibitively slow. NO BACKUP IS TAKEN.",
        ),
    ] = False,
) -> None:
    """
    Run a maintenance script inside the production backend container.

    Takes an automatic pre-execution backup before running, unless
    `--skip-backup` is passed.

    Some scripts accept configuration via environment variables.
    For example, to pass MIN_DATETIME:

    \b
    Linux / macOS:
        MIN_DATETIME=2025-06-01T00:00:00 mascope prod db script run <script>
    Windows PowerShell:
        $env:MIN_DATETIME="2025-06-01T00:00:00"; mascope prod db script run <script>

    \b
    Examples:
        mascope prod db script run populate_none_instrument_function_ids --yes
    """
    if not check_prerequisites(_MODE):
        return

    scripts = _discover_scripts()

    if script not in scripts:
        runtime.logger.error(
            f"Unknown script '{script}'. Run 'mascope prod db script list'."
        )
        raise typer.Exit(1)

    if not yes:
        typer.confirm(
            f"Run '{script}' against prod '{runtime.env.name}'?",
            abort=True,
        )

    db_cfg = runtime.full_config.backend.database

    # --- Backup ---
    if skip_backup:
        runtime.logger.warning(
            "Skipping pre-script backup (--skip-backup). "
            "No restore point will exist if this script corrupts data."
        )
        if not yes:
            typer.confirm(
                f"Run '{script}' against prod '{runtime.env.name}' WITHOUT a backup?",
                abort=True,
            )
    else:
        try:
            container = db_cfg.get_postgres_container_name(_MODE)
            database = db_cfg.get_postgres_database_name(runtime.env.name)
            target_dir, mount = dirs(False, _MODE)
            path = pg_dump(
                container,
                db_cfg.user,
                database,
                target_dir,
                mount,
                label=f"pre-{script}",
            )
            runtime.logger.success(f"Pre-script backup: {path.name}")
        except RuntimeError as e:
            runtime.logger.error(f"Backup failed — aborting: {e}")
            raise typer.Exit(1)

    # --- Execute inside backend container ---
    module = scripts[script]
    backend_container = runtime.full_config.backend.get_backend_container_name(_MODE)
    runtime.logger.info(f"Running in '{backend_container}': {module}")

    # Forward selected host env vars into the container
    env_args: list[str] = []
    for var in _FORWARDED_ENV_VARS:
        val = os.environ.get(var)
        if val is not None:
            env_args += ["-e", f"{var}={val}"]

    result = subprocess.run(
        ["docker", "exec", *env_args, backend_container, _PYTHON, "-m", module],
        check=False,
    )

    if result.returncode != 0:
        runtime.logger.error(f"Script exited with code {result.returncode}")
        raise typer.Exit(result.returncode)

    runtime.logger.success("Script completed")
