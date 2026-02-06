"""
PostgreSQL utilities for development.
"""

import subprocess
import time
from typing import Annotated
import typer

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from mascope_cli.cmd.dev.docker import is_docker_running
from mascope_cli.runtime import runtime


dev_postgres_app = typer.Typer()


def _is_container_running() -> bool:
    """Check if PostgreSQL container is running."""
    container_name = runtime.full_config.backend.database.container_name

    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return container_name in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _is_server_ready() -> bool:
    """
    Check if PostgreSQL server accepts connections.

    Does NOT check if env-specific database exists.
    """
    db_cfg = runtime.full_config.backend.database

    result = subprocess.run(
        [
            "docker",
            "exec",
            db_cfg.container_name,
            "pg_isready",
            "-U",
            db_cfg.user,
            "-h",
            "localhost",
        ],
        capture_output=True,
        timeout=5,
        check=False,
    )

    return result.returncode == 0


def _is_database_ready() -> bool:
    """
    Check if environment-specific database is ready.

    Verifies PostgreSQL accepts connections and database exists.
    """
    db_cfg = runtime.full_config.backend.database
    db_name = db_cfg.get_postgres_database_name(runtime.env.name)

    # Check database exists
    result = subprocess.run(
        [
            "docker",
            "exec",
            db_cfg.container_name,
            "psql",
            "-U",
            db_cfg.user,
            "-lqt",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    return db_name in result.stdout


def _check_prerequisites() -> bool:
    """
    Check if PostgreSQL environment is ready.

    :return: True if all checks pass
    """
    if not (db_cfg := runtime.full_config.backend.database):
        runtime.logger.warning("Database not configured in .mascope.toml")
        return False

    if db_cfg.type != "postgres":
        runtime.logger.warning(f"Database type is '{db_cfg.type}', not 'postgres'")
        return False

    if not is_docker_running():
        runtime.logger.error("Docker daemon is not running")
        runtime.logger.info("Start Docker Desktop first")
        return False

    return True


def wait_for_server(max_wait: int = 30) -> bool:
    """
    Wait for PostgreSQL server to accept connections.

    Does NOT wait for env-specific database (use create_database after this).

    :param max_wait: Maximum seconds to wait
    :return: True if ready within timeout
    """
    runtime.logger.info("Waiting for PostgreSQL...")

    waited = 0
    while waited < max_wait:
        if _is_server_ready():
            runtime.logger.success("PostgreSQL is ready")
            return True

        time.sleep(2)
        waited += 2

    runtime.logger.warning(f"PostgreSQL not ready after {max_wait}s")
    return False


def create_database() -> bool:
    """
    Create environment-specific PostgreSQL database if it doesn't exist.

    Idempotent: Safe to run multiple times, only creates if missing.
    Connects to default 'postgres' database to check and create target database.

    :return: True if database exists or was created successfully
    """
    db_cfg = runtime.full_config.backend.database
    target_db = db_cfg.get_postgres_database_name(runtime.env.name)
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


@dev_postgres_app.callback()
def main():
    """
    PostgreSQL utilities (container managed by docker)
    """


@dev_postgres_app.command()
def status():
    """
    Show PostgreSQL container status and configuration.

    Displays current configuration from .mascope.toml, worker settings,
    and Docker container status.
    """
    if not _check_prerequisites():
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
    runtime.logger.info(f"Container: {db_cfg.container_name}")

    # Display pool configuration
    runtime.logger.info("=== Connection Pool ===")
    runtime.logger.info(f"Pool size: {db_cfg.pool_size}")
    runtime.logger.info(f"Max overflow: {db_cfg.max_overflow}")
    runtime.logger.info(f"Pool timeout: {db_cfg.pool_timeout}s")

    # Status
    runtime.logger.info("=== Status ===")
    if not _is_server_ready():
        runtime.logger.warning("Container not running")
        runtime.logger.info("Run 'mascope dev up' to start")
        return

    if _is_database_ready():
        runtime.logger.success("Env-specific database is ready")
    else:
        runtime.logger.warning("Env-specific database is not ready")
        runtime.logger.info("Check logs: mascope dev postgres logs")


@dev_postgres_app.command()
def logs(
    follow: Annotated[
        bool,
        typer.Option("--follow", "-f", help="Follow log output"),
    ] = False,
    tail: Annotated[
        int,
        typer.Option("--tail", "-n", help="Number of lines to show from the end"),
    ] = 100,
):
    """
    Show PostgreSQL container logs.

    Useful for debugging connection issues or monitoring PostgreSQL activity.
    """
    if not _check_prerequisites():
        return

    if not _is_container_running():
        runtime.logger.warning("Container not running")
        runtime.logger.info("Run 'mascope dev up' to start")
        return

    container_name = runtime.full_config.backend.database.container_name
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


@dev_postgres_app.command()
def cli():
    """
    Open psql CLI inside the container.

    Connects to environment-specific database if ready, falls back to 'postgres' database.

    Example commands:
        \\l                          # List all databases
        \\c mascope_default          # Connect to specific database
        \\dt                         # List tables in current database
        \\d+ table_name              # Describe table structure
        \\du                         # List users
        SELECT version();            # PostgreSQL version
        \\conninfo                   # Connection info
        \\q                          # Quit
    """
    if not _check_prerequisites():
        return

    if not _is_container_running():
        runtime.logger.warning("PostgreSQL container is not running")
        runtime.logger.info("Run 'mascope dev up' first")
        return

    db_cfg = runtime.full_config.backend.database

    # Try env-specific database first, fallback to 'postgres'
    target_db: str
    if _is_database_ready():
        target_db = db_cfg.get_postgres_database_name(runtime.env.name)
        runtime.logger.info(f"Opening psql (database: {target_db})")
    else:
        target_db = "postgres"
        runtime.logger.warning(
            f"Env-specific database not ready, connecting to '{target_db}'"
        )

    runtime.logger.info(
        f"Opening psql CLI (container: {db_cfg.container_name}, database: {target_db})"
    )
    runtime.logger.info("Type '\\q' or press Ctrl+D to close")

    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "-it",
                db_cfg.container_name,
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
        runtime.logger.error("Failed to open psql CLI")
    except KeyboardInterrupt:
        runtime.logger.success("\nClosed psql CLI")


@dev_postgres_app.command()
def create():
    """
    Create environment-specific database if it doesn't exist.

    Useful for manual database setup before running migrations.
    """
    if not _check_prerequisites():
        return

    if not _is_server_ready():
        runtime.logger.warning("Container not running")
        runtime.logger.info("Run 'mascope dev up' first")
        return

    if not _is_database_ready():
        create_database()
    else:
        runtime.logger.error("Database creation failed")
        raise typer.Exit(1)
