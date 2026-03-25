"""
Development database management commands.

Provides commands to manage the development PostgreSQL database: status,
backup, restore, clone, and dump management. The PostgreSQL container is
managed by docker-compose.dev.yaml; this module assumes it is running.

Required compose bind mounts on the postgres service:
    ${MASCOPE_PATH}/.runtime/database/backups/dev:/backups
    ${MASCOPE_PATH}/.runtime/database/transfer:/transfer
"""

import subprocess
import time
from typing import Annotated, Optional

import psycopg2
import typer
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from mascope_cli.pg import (
    check_prerequisites,
    clone_database,
    DatabaseExistsError,
    dirs,
    drop_database,
    is_container_running,
    is_database_ready,
    is_server_ready,
    list_dumps,
    pg_restore,
    validate_env,
)
from mascope_cli.cmd.dev.db.backup import backup_app
from mascope_cli.runtime import runtime


dev_db_app = typer.Typer()
dev_db_app.add_typer(backup_app, name="backup")

_MODE = "dev"

# --- Dev-specific helpers (psycopg2 path — dev port is exposed) ---


def wait_for_server(max_wait: int = 30) -> bool:
    """
    Wait for PostgreSQL server to accept connections.

    Does NOT wait for env-specific database (use create_database after this).

    :param max_wait: Maximum seconds to wait
    :return: True if ready within timeout
    :rtype: bool
    """
    runtime.logger.info("Waiting for PostgreSQL...")

    waited = 0
    while waited < max_wait:
        if is_server_ready(_MODE):
            runtime.logger.success("PostgreSQL is ready")
            return True

        time.sleep(2)
        waited += 2

    runtime.logger.warning(f"PostgreSQL not ready after {max_wait}s")
    return False


def create_database(env: str | None = None) -> bool:
    """
    Create environment-specific PostgreSQL database if it doesn't exist.

    Connects via psycopg2 directly (dev port is exposed). Idempotent, only creates if missing —
    safe to call on every `mascope dev run`.

    For production, use :func:`mascope_cli.pg.admin.create_database` instead,
    which shells out via docker exec (prod port is not exposed).

    :param env: Name of the environment whose database to create.
                Defaults to the active environment (`runtime.env.name`)
                when `None`.
    :type env: str | None
    :return: True if database exists or was created successfully
    :rtype: bool
    """
    db_cfg = runtime.full_config.backend.database
    target_db = db_cfg.get_postgres_database_name(env or runtime.env.name)
    postgres_password = runtime.secret(
        "POSTGRES_PASSWORD_FILE", "postgres_password.txt"
    )

    conn = None
    cursor = None

    try:
        # Connect to default postgres database (always exists)
        conn = psycopg2.connect(
            host=db_cfg.host,
            port=db_cfg.port,
            user=db_cfg.user,
            password=postgres_password,
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if target database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))

        if cursor.fetchone():
            # Database exists - early return
            runtime.logger.debug(f"Database '{target_db}' exists")
            return True

        # Database doesn't exist - create it
        runtime.logger.info(f"Creating database: {target_db}")
        cursor.execute(f'CREATE DATABASE "{target_db}"')
        runtime.logger.success(f"Database '{target_db}' created")
        return True

    except psycopg2.Error as e:
        runtime.logger.error(f"PostgreSQL error: {e}")
        return False

    finally:
        # Clean up connections
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# --- Commands ---


@dev_db_app.callback()
def main() -> None:
    """
    PostgreSQL database management for the development environment.
    """


@dev_db_app.command()
def status() -> None:
    """
    Show PostgreSQL container status and configuration.

    Displays current configuration from .mascope.toml, worker settings,
    and Docker container status.
    """
    if not check_prerequisites(_MODE):
        return

    db_cfg = runtime.full_config.backend.database

    # Display PostgreSQL configuration
    runtime.logger.info("\n=== Database Configuration ===")
    runtime.logger.info(f"Type: {db_cfg.type}")
    runtime.logger.info(f"Host: {db_cfg.host}")
    runtime.logger.info(f"Port: {db_cfg.port}")
    runtime.logger.info(f"User: {db_cfg.user}")
    runtime.logger.info(
        f"DB name: {db_cfg.get_postgres_database_name(runtime.env.name)}"
    )
    runtime.logger.info(f"Container: {db_cfg.get_postgres_container_name('dev')}")

    # Display pool configuration
    runtime.logger.info("=== Connection Pool ===")
    runtime.logger.info(f"Pool size: {db_cfg.pool_size}")
    runtime.logger.info(f"Max overflow: {db_cfg.max_overflow}")
    runtime.logger.info(f"Pool timeout: {db_cfg.pool_timeout}s")

    # Status
    runtime.logger.info("=== Status ===")
    if not is_server_ready(_MODE):
        runtime.logger.warning("Container not running")
        runtime.logger.info("Run 'mascope dev up' to start")
        return

    if is_database_ready(_MODE, runtime.env.name):
        runtime.logger.success("Env-specific database is ready")
    else:
        runtime.logger.warning("Env-specific database is not ready")
        runtime.logger.info("Check logs: mascope dev db logs")


@dev_db_app.command()
def logs(
    follow: Annotated[
        bool,
        typer.Option("--follow", "-f", help="Follow log output"),
    ] = False,
    tail: Annotated[
        int,
        typer.Option("--tail", "-n", help="Number of lines to show from the end"),
    ] = 100,
) -> None:
    """
    Show PostgreSQL container logs.
    """
    if not check_prerequisites(_MODE):
        return

    if not is_container_running(_MODE):
        runtime.logger.warning("Container not running — run 'mascope dev up' to start")
        return

    container_name = runtime.full_config.backend.database.get_postgres_container_name(
        mode=_MODE
    )
    cmd = ["docker", "logs"]

    if follow:
        cmd.append("-f")
    cmd.extend(["--tail", str(tail), container_name])

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        runtime.logger.warning(f"Container '{container_name}' not found")
    except KeyboardInterrupt:
        runtime.logger.success("\nStopped following logs")


@dev_db_app.command()
def cli(
    postgres: Annotated[
        bool,
        typer.Option(
            "--postgres", "-p", help="Connect to the administrative 'postgres' database"
        ),
    ] = False,
) -> None:
    """
    Open a psql shell inside the development PostgreSQL container.

    Connects to the environment-specific database if ready, falls back to
    the default ``postgres`` database otherwise.

    \b
    Example commands:
        \\l                          # List all databases
        \\c mascope_default          # Connect to specific database
        \\dt                         # List tables in current database
        \\d+ table_name              # Describe table structure
        \\du                         # List users
        SELECT version();           # PostgreSQL version
        \\conninfo                   # Connection info
        \\q                          # Quit
    """
    if not check_prerequisites(_MODE):
        return

    if not is_container_running(_MODE):
        runtime.logger.warning("Container not running — run 'mascope dev up' to start")
        return

    db_cfg = runtime.full_config.backend.database

    # Use 'postgres' if flag set or env-specific DB not ready
    target_db = "postgres"
    if not postgres and is_database_ready(_MODE, runtime.env.name):
        target_db = db_cfg.get_postgres_database_name(runtime.env.name)
    elif not postgres:
        runtime.logger.warning(
            f"Env-specific database not ready, connecting to '{target_db}'"
        )

    runtime.logger.info(
        f"Opening psql (container: {db_cfg.get_postgres_container_name(_MODE)}, db: {target_db})"
    )
    runtime.logger.info("Type '\\q' or Ctrl+D to exit")

    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "-it",
                db_cfg.get_postgres_container_name(mode=_MODE),
                "psql",
                "-h",
                "localhost",  # Force TCP/IP connection
                "-U",
                db_cfg.user,
                "-d",
                target_db,
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        runtime.logger.error("Failed to open psql shell")
    except KeyboardInterrupt:
        runtime.logger.success("\nClosed psql shell")


@dev_db_app.command()
def create(
    env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help=(
                "Environment whose database to create. Defaults to the active environment. "
                "Does not change the active environment."
            ),
        ),
    ] = None,
):
    """
    Create an environment's database if it doesn't exist.

    By default creates the active environment's database. Use --env to create
    a database for a different environment without changing the active one.

    Idempotent — safe to run multiple times.

    \b
    Examples:
        mascope dev db create               # create active env database
        mascope dev db create --env test    # create test env database
    """
    if not check_prerequisites(_MODE):
        return

    if not is_server_ready(_MODE):
        runtime.logger.warning("Container not running — run 'mascope dev up' to start")
        return

    db_cfg = runtime.full_config.backend.database
    target_env = env or runtime.env.name

    if not validate_env(target_env):
        runtime.logger.error(
            f"Environment '{target_env}' not found.\n"
            f"Available: {', '.join(e['name'] for e in runtime.env.list)}"
        )
        raise typer.Exit(1)

    db_name = db_cfg.get_postgres_database_name(target_env)

    if is_database_ready(_MODE, target_env):
        runtime.logger.info(f"Database '{db_name}' already exists")
        return

    if not create_database(target_env):
        runtime.logger.error(f"Failed to create database '{db_name}'")
        raise typer.Exit(1)


@dev_db_app.command()
def drop(
    env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help=(
                "Environment which database to drop. Defaults to the active environment. "
                "Does not change the active environment."
            ),
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """
    Drop an environment's database, terminating all active connections first.

    By default drops the active environment's database. Use --env to target
    a different environment without changing the active one.

    All data is permanently deleted. Use backup first if needed.

    \b
    Examples:
        mascope dev db drop                  # drop active env database
        mascope dev db drop --env test       # drop test env database
        mascope dev db drop --env test --yes # skip confirmation
    """
    if not check_prerequisites(_MODE):
        return
    if not is_server_ready(_MODE):
        runtime.logger.error("PostgreSQL not running — run 'mascope dev up' first")
        raise typer.Exit(1)

    db_cfg = runtime.full_config.backend.database
    target_env = env or runtime.env.name

    if not validate_env(target_env):
        runtime.logger.error(
            f"Environment '{target_env}' not found.\n"
            f"Available: {', '.join(e['name'] for e in runtime.env.list)}"
        )
        raise typer.Exit(1)

    container = db_cfg.get_postgres_container_name(mode=_MODE)
    database = db_cfg.get_postgres_database_name(target_env)

    if not yes:
        typer.confirm(
            f"Drop database '{database}'? All data will be permanently deleted.",
            abort=True,
        )

    try:
        runtime.logger.info(f"Terminating connections and dropping '{database}'...")
        drop_database(container, db_cfg.user, database)
    except RuntimeError as e:
        runtime.logger.error(str(e))
        raise typer.Exit(1)

    runtime.logger.success(f"Database '{database}' dropped")


@dev_db_app.command()
def restore(
    dump_file: Annotated[
        Optional[str],
        typer.Argument(
            help=(
                "Dump filename (basename only, e.g. 'mascope_default_20250101_040000.dump'). "
                "Omit to use the latest available dump for the target environment."
            ),
        ),
    ] = None,
    env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help=(
                "Environment to restore into. Defaults to the active environment. "
                "Does not change the active environment."
            ),
        ),
    ] = None,
    transfer: Annotated[
        bool,
        typer.Option(
            "--transfer",
            "-t",
            help=(
                "Read the dump from the transfer directory (.runtime/database/transfer/) "
                "instead of the regular backup directory."
            ),
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """
    Restore an environment's database from a backup dump file.

    Drops and recreates the target database, then restores from the specified
    dump. All current data in the target is replaced.

    By default restores into the active environment. Use --env to
    restore into a different environment without changing the active one.

    By default reads from .runtime/database/backups/dev/. Use --transfer to
    read from .runtime/database/transfer/ (for cross-server sync flows).

    Omit `dump_file` to automatically use the latest available dump for the
    target environment.
    """
    if not check_prerequisites(_MODE):
        return
    if not is_server_ready(_MODE):
        runtime.logger.error("PostgreSQL not running — run 'mascope dev up' first")
        raise typer.Exit(1)

    db_cfg = runtime.full_config.backend.database
    target_env = env or runtime.env.name

    if not validate_env(target_env):
        runtime.logger.error(
            f"Target environment '{target_env}' not found.\n"
            f"Available: {', '.join(e['name'] for e in runtime.env.list)}"
        )
        raise typer.Exit(1)

    container = db_cfg.get_postgres_container_name(mode=_MODE)
    database = db_cfg.get_postgres_database_name(target_env)
    source_dir, mount = dirs(transfer, _MODE)

    # Resolve which backup file to use
    if dump_file:
        resolved = source_dir / dump_file
        if not resolved.exists():
            runtime.logger.error(f"Dump file not found: {resolved}")
            raise typer.Exit(1)
    else:
        available = list_dumps(source_dir, db_name_filter=database)
        if not available:
            runtime.logger.error(f"No backups found for '{database}' in {source_dir}")
            raise typer.Exit(1)
        resolved = available[0]
        runtime.logger.info(f"Latest dump: {resolved.name}")

    if not yes:
        typer.confirm(
            f"Drop and restore '{database}' from '{resolved.name}'?\n"
            f"All current data will be replaced.",
            abort=True,
        )

    try:
        runtime.logger.info(f"Terminating connections and dropping '{database}'...")
        drop_database(container, db_cfg.user, database)

        runtime.logger.info(f"Creating empty '{database}'...")
        # psycopg2-based path: dev port is exposed, provides idempotency check
        if not create_database(target_env):
            raise RuntimeError(f"Failed to recreate database '{database}' after drop")

        runtime.logger.info(f"Restoring from '{resolved.name}'...")
        pg_restore(container, db_cfg.user, database, resolved, mount)

    except (RuntimeError, FileNotFoundError) as e:
        runtime.logger.error(str(e))
        raise typer.Exit(1)

    runtime.logger.success(
        f"Database {database} restored from {resolved.name} successfully"
    )


@dev_db_app.command()
def clone(
    target_env: Annotated[
        str,
        typer.Argument(
            help=(
                "Target environment name (e.g. 'staging', 'test-env'). "
                "The database name is derived automatically."
            ),
        ),
    ],
    source_env: Annotated[
        Optional[str],
        typer.Option(
            "--source",
            "-s",
            help=(
                "Source environment name. Defaults to the currently active "
                "environment if not specified."
            ),
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt if target database already exists.",
        ),
    ] = False,
) -> None:
    """
    Clone one environment's database to another environment on the same server.

    Both source and target are specified as environment names — the database
    names are derived automatically using the standard naming convention
    (`mascope_{env_name}`).

    Requires zero active connections to the source database at the time of cloning.

    If the target database already exists, a confirmation prompt is shown
    before dropping and recreating it. Use `--yes` to skip the prompt.

    For cloning between dev and prod postgres servers, use env sync instead.

    \b
    Examples:
        mascope dev db clone test                 # clone active env → test
        mascope dev db clone test --yes           # overwrite test without prompt
        mascope dev db clone test --source orbi2  # clone orbi2 env → test
    """
    if not check_prerequisites(_MODE):
        return
    if not is_server_ready(_MODE):
        runtime.logger.error("PostgreSQL not running — run 'mascope dev up' first")
        raise typer.Exit(1)

    db_cfg = runtime.full_config.backend.database
    container = db_cfg.get_postgres_container_name(mode=_MODE)
    resolved_source_env = source_env or runtime.env.name

    if not validate_env(resolved_source_env):
        runtime.logger.error(
            f"Source environment '{source_env}' not found.\n"
            f"Available: {', '.join(e['name'] for e in runtime.env.list)}"
        )
        raise typer.Exit(1)

    if not validate_env(target_env):
        runtime.logger.error(
            f"Target environment '{target_env}' not found.\n"
            f"Available: {', '.join(e['name'] for e in runtime.env.list)}\n"
            f"Create it first with 'mascope env create {target_env}'."
        )
        raise typer.Exit(1)

    source_db = db_cfg.get_postgres_database_name(resolved_source_env)
    target_db = db_cfg.get_postgres_database_name(target_env)

    if source_db == target_db:
        runtime.logger.error("Source and target resolve to the same database.")
        raise typer.Exit(1)

    runtime.logger.info(f"Cloning '{source_db}' → '{target_db}'...")

    try:
        clone_database(container, db_cfg.user, source_db, target_db)

    except DatabaseExistsError as e:
        # Target exists — prompt to overwrite unless --yes given
        if not yes:
            typer.confirm(
                f"Target database '{e.database}' already exists. Drop it and replace with clone?",
                abort=True,
            )
        try:
            runtime.logger.info(f"Dropping existing '{target_db}'...")
            drop_database(container, db_cfg.user, target_db)
            runtime.logger.info(f"Cloning '{source_db}' → '{target_db}'...")
            clone_database(container, db_cfg.user, source_db, target_db)
        except RuntimeError as inner:
            runtime.logger.error(str(inner))
            raise typer.Exit(1)

    except RuntimeError as e:
        runtime.logger.error(str(e))
        raise typer.Exit(1)

    runtime.logger.success(f"Clone complete: '{source_db}' → '{target_db}'")
