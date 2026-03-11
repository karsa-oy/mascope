"""
Development database backup management commands.

Registered as the `backup` subgroup under `mascope dev db`.
Provides commands to create, list, and delete backup dump files for the
development PostgreSQL container.

Dump directories:
    .runtime/database/backups/dev/   — default backup storage
    .runtime/database/transfer/      — staging for cross-server sync (--transfer)
"""

from datetime import datetime, timedelta
from typing import Annotated, Optional

import typer

from mascope_cli.pg import (
    dirs,
    is_database_ready,
    is_server_ready,
    list_dumps,
    pg_dump,
    purge_old_dumps,
    validate_env,
)
from mascope_cli.runtime import runtime

backup_app = typer.Typer()

_MODE = "dev"


@backup_app.callback()
def main() -> None:
    """
    Backup management for the development database.

    \b
    Commands:
        mascope dev db backup create              # dump active env database
        mascope dev db backup list                # list available dumps
        mascope dev db backup delete              # delete old dumps
    """


@backup_app.command(name="create")
def backup_create(
    env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help=(
                "Environment to back up. Defaults to the active environment. "
                "Does not change the active environment."
            ),
        ),
    ] = None,
    label: Annotated[
        str,
        typer.Option(
            "--label",
            "-l",
            help="Label embedded in the dump filename (e.g. 'pre-migration').",
        ),
    ] = "",
    transfer: Annotated[
        bool,
        typer.Option(
            "--transfer",
            "-t",
            help=(
                "Write the dump to the transfer directory (.runtime/database/transfer/) "
                "instead of the regular backup directory. Use for cross-server sync staging."
            ),
        ),
    ] = False,
) -> None:
    """
    Dump the environment's database to a compressed .dump file.

    By default backs up the active environment. Use --env to back up a
    different environment without changing the active one.

    Dumps are written to .runtime/database/backups/dev/ by default.
    Use --transfer to write to .runtime/database/transfer/ instead,
    which is the shared staging directory for cross-server sync.

    \b
    Examples:
        mascope dev db backup create
        mascope dev db backup create --env orbi2
        mascope dev db backup create --label pre-migration
        mascope dev db backup create --transfer
    """
    db_cfg = runtime.full_config.backend.database
    source_env = env or runtime.env.name

    if not validate_env(source_env):
        runtime.logger.error(
            f"Environment '{source_env}' not found.\n"
            f"Available: {', '.join(e['name'] for e in runtime.env.list)}"
        )
        raise typer.Exit(1)

    if not is_server_ready(_MODE):
        runtime.logger.error("PostgreSQL not running — run 'mascope dev up' first")
        raise typer.Exit(1)

    if not is_database_ready(_MODE, source_env):
        runtime.logger.error(f"Database for env '{source_env}' does not exist")
        raise typer.Exit(1)

    container = db_cfg.get_postgres_container_name(mode=_MODE)
    database = db_cfg.get_postgres_database_name(source_env)
    dump_dir, mount = dirs(transfer, _MODE)

    runtime.logger.info(f"Backing up '{database}' → {dump_dir.name}/...")
    try:
        path = pg_dump(container, db_cfg.user, database, dump_dir, mount, label)
    except RuntimeError as e:
        runtime.logger.error(str(e))
        raise typer.Exit(1)

    size_mb = path.stat().st_size / 1024 / 1024
    runtime.logger.success(f"Backup created: {path.name}  ({size_mb:.1f} MB)")


@backup_app.command(name="list")
def backup_list(
    env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help="Filter by environment. Defaults to the active environment.",
        ),
    ] = None,
    all_dbs: Annotated[
        bool,
        typer.Option("--all", "-a", help="List backups for all environments."),
    ] = False,
    transfer: Annotated[
        bool,
        typer.Option("--transfer", "-t", help="List from the transfer directory."),
    ] = False,
) -> None:
    """
    List available backup dump files.

    By default lists from .runtime/database/backups/dev/ filtered to the
    active environment. Use --transfer to list from the transfer directory.
    Use --all to show all environments.

    \b
    Examples:
        mascope dev db backup list
        mascope dev db backup list --all
        mascope dev db backup list --transfer
        mascope dev db backup list --env orbi2
    """
    db_cfg = runtime.full_config.backend.database
    source_env = env or runtime.env.name
    database = db_cfg.get_postgres_database_name(source_env)
    db_filter = None if all_dbs else database
    target_dir, _ = dirs(transfer, _MODE)

    dumps = list_dumps(target_dir, db_name_filter=db_filter)
    if not dumps:
        runtime.logger.info("No backups found")
        return

    for f in dumps:
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_mb = f.stat().st_size / 1024 / 1024
        runtime.logger.info(f"  {f.name:<60}  {size_mb:>6.1f} MB  {mtime}")


@backup_app.command(name="delete")
def backup_delete(
    retention_days: Annotated[
        int,
        typer.Option(
            "--retention-days",
            "-r",
            help="Delete backups older than N days.",
        ),
    ] = 30,
    env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help="Filter by environment. Defaults to the active environment.",
        ),
    ] = None,
    transfer: Annotated[
        bool,
        typer.Option(
            "--transfer",
            "-t",
            help="Delete from the transfer directory instead of the regular backup directory.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show which files would be deleted without actually deleting them.",
        ),
    ] = False,
) -> None:
    """
    Delete old dump files beyond the retention window.

    Only affects dumps for the active environment (or --env if specified).
    Other environments' dumps in the same directory are not touched.

    Dumps are deleted from .runtime/database/backups/dev/ by default.
    Use --transfer to delete from .runtime/database/transfer/ instead.

    Use --dry-run to preview what would be removed before committing.

    \b
    Examples:
        mascope dev db backup delete --retention-days 7
        mascope dev db backup delete --transfer --retention-days 3
        mascope dev db backup delete --env orbi2 --dry-run
    """
    db_cfg = runtime.full_config.backend.database
    source_env = env or runtime.env.name

    if not validate_env(source_env):
        runtime.logger.error(
            f"Environment '{source_env}' not found.\n"
            f"Available: {', '.join(e['name'] for e in runtime.env.list)}"
        )
        raise typer.Exit(1)

    database = db_cfg.get_postgres_database_name(source_env)
    target_dir, _ = dirs(transfer, _MODE)
    cutoff = datetime.now() - timedelta(days=retention_days)

    candidates = [
        f
        for f in list_dumps(target_dir, db_name_filter=database)
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff
    ]

    if not candidates:
        runtime.logger.info(f"No backups older than {retention_days} days found")
        return

    if dry_run:
        runtime.logger.info(f"Would delete {len(candidates)} backup(s):")
        for f in candidates:
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            runtime.logger.info(f"  {f.name}  ({mtime})")
        return

    deleted = purge_old_dumps(target_dir, database, retention_days)
    for d in deleted:
        runtime.logger.info(f"Deleted: {d.name}")
    runtime.logger.success(f"Deleted {len(deleted)} backup(s)")
