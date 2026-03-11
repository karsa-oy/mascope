"""
Runtime environment management commands.

Provides commands to list, activate, and sync Mascope runtime environments.
Environments are named directories under `{MASCOPE_PATH}/.runtime/env/`,
each containing all state required to run Mascope services (sqlite database,
filestore, streaming folders).
"""

from typing import Annotated
import typer

from rich.console import Console
from rich.table import Table

from mascope_cli.runtime import runtime
from mascope_cli.cmd.env._sync import sync_db, sync_filestore
from mascope_runtime import Runtime


env_app = typer.Typer()


@env_app.callback()
def main():
    """
    Manage your mascope runtime environments.

    Runtime envs are folders in the `.runtime/env` directory under your
    `MASCOPE_PATH`. They contain all the state needed to run Mascope apps
    and/or services, e.g. the sqlite database, file stores, and file streaming folders.
    """


# --- Internal helpers ---


def _complete_env() -> list[str]:
    """
    Return available environment names for shell autocompletion.

    :return: List of environment names from the `.runtime/env/` directory.
    :rtype: list[str]
    """
    return [e["name"] for e in runtime.env.list]


# --- Commands ---


@env_app.command(name="list")
def list_envs():
    """
    List available envs.

    Displays name, description, path, and status for each environment.
    The active environment is marked with `*`.
    """
    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Path", style="magenta", no_wrap=True)
    table.add_column("Status", style="cyan", no_wrap=True)
    for env in runtime.env.list:
        env_runtime = Runtime("cli", env=env["name"])
        is_selected = env["name"] == runtime.state.env
        default = "default" if env["name"] == "default" else None
        active = "active" if is_selected else None
        status = default or active
        selected = "*" if is_selected else ""
        table.add_row(
            env["name"] + selected,
            env_runtime.meta.description or "n/a",
            env["path"],
            status,
        )
    console = Console()
    console.print(table)


@env_app.command()
def use(
    env: Annotated[
        str,
        typer.Argument(
            help="The environment to activate.",
            autocompletion=_complete_env,
        ),
    ],
) -> None:
    """
    Activate an env so that it is used in all subsequent commands.

    Writes the selected environment name to `state.json`. Persists across
    CLI invocations until changed again.

    \b
    Examples:
        mascope env use tof1
        mascope env use default
    """
    if env in [e["name"] for e in runtime.env.list]:
        runtime.state.env = env
        runtime.logger.info(f"Mascope env set to '{env}'")
    else:
        runtime.logger.error(f"No env named '{env}' was found")


@env_app.command()
def sync(
    source_env: Annotated[
        str,
        typer.Argument(
            metavar="SOURCE_ENV",
            help=(
                "Source environment. Local name (e.g. `tof1`) or remote "
                "address in `USER@HOST:ENV` format (e.g. `karsa@192.168.1.88:tof1`)."
            ),
        ),
    ],
    source_mode: Annotated[
        str,
        typer.Argument(
            metavar="SOURCE_MODE",
            help="Mode of the source PostgreSQL server: `dev` or `prod`.",
        ),
    ],
    target_env: Annotated[
        str,
        typer.Argument(
            metavar="TARGET_ENV",
            help=(
                "Target environment. Local name (e.g. `tof1`) or remote "
                "address in `USER@HOST:ENV` format."
            ),
        ),
    ],
    target_mode: Annotated[
        str,
        typer.Argument(
            metavar="TARGET_MODE",
            help="Mode of the target PostgreSQL server: `dev` or `prod`.",
        ),
    ],
    skip_filestore: Annotated[
        bool,
        typer.Option(
            "--skip-filestore",
            "-sf",
            help="Skip synchronizing the filestore.",
        ),
    ] = False,
    skip_db: Annotated[
        bool,
        typer.Option(
            "--skip-db",
            "-sd",
            help="Skip synchronizing the PostgreSQL database.",
        ),
    ] = False,
):
    """
    Sync a runtime env from source to target.

    Both source and target accept a local environment name or a remote address
    in `USER@HOST:ENV` format. Both require an explicit mode (`dev` or `prod`)
    to identify which PostgreSQL server to use — no defaults are applied.

    By default, both the filestore (via rsync) and the database (via
    pg_dump/pg_restore through a staging transfer directory) are synced.
    Use `--skip-filestore` or `--skip-db` to opt out of either.

    The database sync always stages through `.runtime/database/transfer/`.
    On success, the transfer dump is deleted and 7-day retention pruning runs.
    On failure, the dump is preserved for manual recovery.

    Remote → remote sync is not supported — run from one of the machines.

    \b
    Examples:
        mascope env sync karsa@192.168.1.88:tof1 prod tof1 dev
        mascope env sync tof1 prod tof1 dev
        mascope env sync tof1 dev test-env dev
        mascope env sync tof1 prod karsa@192.168.1.88:tof1 prod
        mascope env sync karsa@192.168.1.88:tof1 prod tof1 dev --skip-filestore
        mascope env sync tof1 dev test-env dev --skip-db
    """
    if source_mode not in ("dev", "prod"):
        runtime.logger.error(
            f"Invalid SOURCE_MODE '{source_mode}' — must be 'dev' or 'prod'."
        )
        raise typer.Exit(1)

    if target_mode not in ("dev", "prod"):
        runtime.logger.error(
            f"Invalid TARGET_MODE '{target_mode}' — must be 'dev' or 'prod'."
        )
        raise typer.Exit(1)

    errors: list[str] = []

    if not skip_filestore:
        runtime.logger.info("--- Filestore sync ---")
        try:
            sync_filestore(source_env, target_env)
        except Exception as e:
            runtime.logger.error(f"Filestore sync failed: {e}")
            errors.append("filestore")

    if not skip_db:
        runtime.logger.info("--- Database sync ---")
        try:
            sync_db(source_env, source_mode, target_env, target_mode)
        except (ValueError, RuntimeError) as e:
            runtime.logger.error(f"Database sync failed: {e}")
            errors.append("database")

    if errors:
        runtime.logger.error(f"Sync completed with errors in: {', '.join(errors)}")
        raise typer.Exit(1)

    runtime.logger.success(
        f"Sync complete: {source_env} ({source_mode}) → {target_env} ({target_mode})"
    )
