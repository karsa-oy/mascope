"""
Shared PostgreSQL CLI utilities.

Helpers used by both `mascope dev db` and `mascope prod db` commands.
All functions that differ only by `mode` string live here to avoid
duplication between the two CLI modules.

Design constraints:
- No Typer imports — these are pure helpers, not commands.
- All functions accept `mode` explicitly; callers hold `_MODE` constants.
- `runtime` is imported as the module-level singleton; functions read
  `runtime.full_config` at call time (after `runtime.reload()`), so
  config is always current.
"""

import subprocess
from pathlib import Path

from mascope_cli.cmd.dev.docker import is_docker_running

from mascope_cli.runtime import runtime


def check_prerequisites(mode: str, check_docker_desktop: bool = False) -> bool:
    """
    Validate that the PostgreSQL environment is configured and reachable.

    Checks performed:
    - Database section present in resolved config.
    - Database type is `postgres`.
    - Docker daemon is running (always checked via `docker info`).
    - On developer machines (`check_docker_desktop=True`), also verifies
      Docker Desktop is running — relevant for Windows/macOS where the daemon
      only starts when the Desktop app is open.

    :param mode: Runtime mode, `"dev"` or `"prod"`. Used only for
                 log messages; config is already resolved by the time this
                 runs.
    :type mode: str
    :param check_docker_desktop: If `True`, call `is_docker_running()` from the dev docker
                                 module, which performs the Desktop-specific
                                 check. Pass `True` for dev, `False` for
                                 prod (Linux server, no Desktop).
    :type check_docker_desktop: bool
    :return: `True` if all checks pass, `False` otherwise.
    :rtype: bool
    """
    if not (db_cfg := runtime.full_config.backend.database):
        runtime.logger.warning("Database not configured in .mascope.toml")
        return False

    if db_cfg.type != "postgres":
        runtime.logger.warning(
            f"Database type is '{db_cfg.type}', not 'postgres' — "
            f"mascope {mode} db commands require PostgreSQL"
        )
        return False

    if check_docker_desktop:
        if not is_docker_running():
            runtime.logger.error("Docker daemon is not running")
            runtime.logger.info("Start Docker Desktop first")
            return False
    else:
        # On prod (Linux server), verify docker CLI is functional
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            runtime.logger.error("Docker daemon is not running or not accessible")
            return False

    return True


def is_container_running(mode: str) -> bool:
    """
    Check whether the PostgreSQL container for the given mode is running.

    :param mode: Runtime mode, `"dev"` or `"prod"`.
    :type mode: str
    :return: `True` if the container is listed in `docker ps` output.
    :rtype: bool
    """
    container = runtime.full_config.backend.database.get_postgres_container_name(
        mode=mode
    )
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return container in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_server_ready(mode: str) -> bool:
    """
    Check whether the PostgreSQL server accepts connections.

    Uses `pg_isready` via `docker exec` — works regardless of whether
    the container port is exposed to the host.

    Does NOT verify whether a specific database exists; use
    :func:`is_database_ready` for that.

    :param mode: Runtime mode, `"dev"` or `"prod"`.
    :type mode: str
    :return: `True` if `pg_isready` exits 0.
    :rtype: bool
    """
    db_cfg = runtime.full_config.backend.database
    result = subprocess.run(
        [
            "docker",
            "exec",
            db_cfg.get_postgres_container_name(mode=mode),
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


def is_database_ready(mode: str, env: str) -> bool:
    """
    Check whether the database for a specific environment exists on the server.

    Uses `psql -lqt` via `docker exec` — works regardless of port exposure.
    Accepts an explicit `env` so callers can check any environment,
    not just the currently active one (e.g. when `--env` flag is passed).

    :param mode: Runtime mode, `"dev"` or `"prod"`.
    :type mode: str
    :param env: Name of the runtime environment whose database to check
                     (e.g. `"default"`, `"tof1"`).
    :type env: str
    :return: `True` if the database name appears in `psql -lqt` output.
    :rtype: bool
    """
    db_cfg = runtime.full_config.backend.database
    db_name = db_cfg.get_postgres_database_name(env)

    result = subprocess.run(
        [
            "docker",
            "exec",
            db_cfg.get_postgres_container_name(mode=mode),
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


def validate_env(env: str) -> bool:
    """
    Check that `env` exists among the configured runtime environments.

    Reads `runtime.env.list`, which scans the `.runtime/env/` directory
    for subdirectories.

    :param env: Environment name to validate (e.g. `"tof1"`).
    :type env: str
    :return: `True` if a matching environment directory exists.
    :rtype: bool
    """
    available = [e["name"] for e in runtime.env.list]
    return env in available


def dirs(transfer: bool, mode: str) -> tuple[Path, str]:
    """
    Resolve the dump directory and container mount point for the given context.

    Returns the transfer directory and mount when `transfer=True`, otherwise
    the mode-specific backups directory and its mount.

    :param transfer: If `True`, return the shared transfer dir and mount
                     used for cross-server sync staging. If `False`, return
                     the mode-specific backup dir.
    :type transfer: bool
    :param mode: Runtime mode, `"dev"` or `"prod"`. Determines the backup
                 subdirectory (e.g. `.runtime/database/backups/prod/`).
    :type mode: str
    :return: `(host_path, container_mount)` — host path and container mount
             point to pass to :func:`mascope_cli.pg.admin.pg_dump` /
             :func:`mascope_cli.pg.admin.pg_restore`.
    :rtype: tuple[Path, str]
    """
    db_cfg = runtime.full_config.backend.database
    if transfer:
        return db_cfg.get_transfer_dir(), db_cfg.get_transfer_mount()
    return db_cfg.get_backups_dir(mode=mode), db_cfg.get_backups_mount()
