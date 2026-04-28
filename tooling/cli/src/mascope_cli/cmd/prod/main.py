"""
Production environment management commands.

Provides commands to manage Mascope production services via docker compose.
Wraps the most common compose operations as explicit subcommands and exposes
a `docker` escape hatch for arbitrary compose passthrough.

Common operations:
    mascope prod up
    mascope prod up --build
    mascope prod down
    mascope prod ps
    mascope prod build
    mascope prod logs --follow
    mascope prod restart postgres
    mascope prod docker exec -it postgres bash

Database management:
    mascope prod db status
    mascope prod db backup
    mascope prod db restore --yes
"""

import os
import platform
import time
from typing import Annotated, Optional

import typer

from mascope_cli.cmd import lib
from mascope_cli.cmd.prod.db import prod_db_app
from mascope_cli.runtime import runtime
from mascope_runtime import Runtime


_MODE = "prod"

# Resolved once at import time — MASCOPE_PATH is guaranteed to be set
# by the time any CLI command runs.
_COMPOSE_PATH = os.path.join(
    *os.path.split(os.environ["MASCOPE_PATH"]), "docker-compose.yaml"
)

prod_app = typer.Typer()
prod_app.add_typer(prod_db_app, name="db")


#  --- Callback — runs before every prod subcommand ---


@prod_app.callback()
def main() -> None:
    """
    Manage the Mascope production environment.

    Wraps the most common `docker compose` operations as named subcommands.
    For anything not covered, use `mascope prod docker <args>` to pass
    arbitrary arguments directly to `docker compose`.

    \b
    Compose commands (run `mascope prod <cmd> --help` for details):
        mascope prod up
        mascope prod up --build
        mascope prod down
        mascope prod ps
        mascope prod build
        mascope prod logs --follow backend
        mascope prod restart postgres
        mascope prod docker exec -it postgres bash

    \b
    Database management (run `mascope prod db --help` for details):
        mascope prod db status
        mascope prod db backup
        mascope prod db restore --yes
    """
    # Override mode without writing to state.json — prevents state.json from a
    # previous dev/prod run from contaminating this invocation's config.
    runtime.state.override("mode", _MODE)
    runtime.reload_config()
    runtime.logger.info(
        f'Running at env "{runtime.env.name}" in {runtime.state.mode} mode'
    )


#  --- Internal helpers ---


def _compose_env() -> dict[str, str]:
    """
    Build the environment variable dict injected into every docker compose call.

    Resolves all runtime config, container names, and build arguments required
    by the production compose file. Must be called after `runtime.reload_config()`
    so that prod-mode config is active.

    :return: Mapping of environment variable names to their resolved values.
    :rtype: dict[str, str]
    """
    db_cfg = runtime.full_config.backend.database
    backend_cfg = runtime.full_config.backend
    file_converter_cfg = runtime.full_config.file_converter
    frontend_cfg = runtime.full_config.frontend
    redis_cfg = runtime.full_config.backend.redis

    db_name = db_cfg.get_postgres_database_name(env_name=runtime.env.name)

    # Instantiated with log=False to avoid duplicate log configuration.
    # mode=_MODE passed explicitly so this temporary instance uses prod config
    # without touching state.json.
    frontend_runtime = Runtime("frontend", mode=_MODE, log=False)
    mascope_runtime = frontend_runtime.module.to_json()

    if platform.system() != "Windows":
        # On Unix, inherit OS timezone
        timezone = "/".join(time.tzname)
    else:
        # Windows uses a different timezone system than Linux/macOS; converting
        # from the Windows format proved difficult, and the app is deployed on
        # Linux anyway, so Etc/UTC is a safe default.
        timezone = "Etc/UTC"

    return dict(
        MASCOPE_ENV=runtime.env.name,
        MASCOPE_PATH=os.environ["MASCOPE_PATH"],
        MASCOPE_RUNTIME=mascope_runtime,
        MASCOPE_FILESTORE=runtime.meta.filestore,
        MASCOPE_TIMEZONE=timezone,
        # Forwarded explicitly so compose variable interpolation is always
        # satisfied — empty string when --log-level was not passed, which
        # compose treats as "no override" for the container environment.
        MASCOPE_LOGLEVEL=os.environ.get("MASCOPE_LOGLEVEL", ""),
        # --- Db settings ---
        MASCOPE_DB_NAME=db_name,
        MASCOPE_DB_USER=db_cfg.user,
        MASCOPE_DB_CONTAINER_NAME=db_cfg.get_postgres_container_name(mode=_MODE),
        MASCOPE_DB_SHM_SIZE=db_cfg.shm_size,
        MASCOPE_DB_SHARED_BUFFERS=db_cfg.shared_buffers,
        MASCOPE_DB_EFFECTIVE_CACHE_SIZE=db_cfg.effective_cache_size,
        MASCOPE_DB_WORK_MEM=db_cfg.work_mem,
        MASCOPE_DB_MAINTENANCE_WORK_MEM=db_cfg.maintenance_work_mem,
        MASCOPE_DB_AUTOVACUUM_WORK_MEM=db_cfg.autovacuum_work_mem,
        MASCOPE_DB_WAL_BUFFERS=db_cfg.wal_buffers,
        MASCOPE_DB_MIN_WAL_SIZE=db_cfg.min_wal_size,
        MASCOPE_DB_MAX_WAL_SIZE=db_cfg.max_wal_size,
        MASCOPE_DB_CHECKPOINT_COMPLETION_TARGET=str(
            db_cfg.checkpoint_completion_target
        ),
        MASCOPE_DB_WAL_COMPRESSION=db_cfg.wal_compression,
        MASCOPE_DB_EFFECTIVE_IO_CONCURRENCY=str(db_cfg.effective_io_concurrency),
        MASCOPE_DB_RANDOM_PAGE_COST=str(db_cfg.random_page_cost),
        MASCOPE_DB_DEFAULT_STATISTICS_TARGET=str(db_cfg.default_statistics_target),
        MASCOPE_DB_JIT=db_cfg.jit,
        MASCOPE_DB_AUTOVACUUM_MAX_WORKERS=str(db_cfg.autovacuum_max_workers),
        # --- Container names ---
        MASCOPE_REDIS_CONTAINER_NAME=redis_cfg.get_redis_container_name(mode=_MODE),
        MASCOPE_BACKEND_CONTAINER_NAME=backend_cfg.get_backend_container_name(
            mode=_MODE
        ),
        MASCOPE_FILE_CONVERTER_CONTAINER_NAME=file_converter_cfg.get_file_converter_container_name(
            mode=_MODE
        ),
        MASCOPE_FRONTEND_CONTAINER_NAME=frontend_cfg.get_frontend_container_name(
            mode=_MODE
        ),
    )


def _run_compose(args: list[str]) -> None:
    """
    Invoke `docker compose` against the production compose file.

    Builds the full environment variable dict and delegates to `lib.run`.
    Mode override and config reload are handled in the callback — by the
    time any command calls this, config is already prod-scoped.

    :param args: docker compose subcommand and arguments,
                 e.g. `["up", "--detach"]` or `["logs", "--follow", "backend"]`.
    :type args: list[str]
    """
    env_vars = _compose_env()
    command = f"docker compose --file '{_COMPOSE_PATH}' {' '.join(args)}"

    runtime.logger.info(
        f"Database: {env_vars['MASCOPE_DB_NAME']}."
        f" Timezone: {env_vars['MASCOPE_TIMEZONE']}."
        f" Command: {command}"
    )

    lib.run(command=command, env_vars=env_vars)


# --- Commands ---


@prod_app.command()
def up(
    rebuild: Annotated[
        bool,
        typer.Option("--build", help="Build images before starting containers."),
    ] = False,
    detach: Annotated[
        bool,
        typer.Option("--detach", "-d", help="Stream container logs after starting."),
    ] = False,
) -> None:
    """
    Start production containers.

    Streams logs to terminal by default (foreground). Pass --detach to run
    in the background and return the terminal immediately.

    \b
    Examples:
        mascope prod up
        mascope prod up --build
        mascope prod up --detach
        mascope prod up --build --detach
    """
    args = ["up"]
    if rebuild:
        args.append("--build")
    if detach:
        args.append("--detach")
    _run_compose(args)


@prod_app.command()
def down() -> None:
    """
    Stop and remove production containers.

    Runs `docker compose down`. Does not remove volumes or images.

    \b
    Examples:
        mascope prod down
    """
    _run_compose(["down"])


@prod_app.command()
def ps() -> None:
    """
    Show production container status.

    Runs `docker compose ps`.

    \b
    Examples:
        mascope prod ps
    """
    _run_compose(["ps"])


@prod_app.command()
def build() -> None:
    """
    Build production container images.

    Runs `docker compose build`. Use `mascope prod up --build` to build
    and start in one step.

    \b
    Examples:
        mascope prod build
    """
    _run_compose(["build"])


@prod_app.command()
def logs(
    follow: Annotated[
        bool,
        typer.Option("--follow", "-f", help="Follow log output."),
    ] = False,
    tail: Annotated[
        int,
        typer.Option("--tail", "-n", help="Number of lines to show from end of logs."),
    ] = 100,
    service: Annotated[
        Optional[str],
        typer.Argument(help="Service name to filter logs (e.g. postgres, backend)."),
    ] = None,
) -> None:
    """
    Show production container logs.

    Runs `docker compose logs`. Optionally filter by service name and follow
    output in real time.

    \b
    Examples:
        mascope prod logs
        mascope prod logs --follow
        mascope prod logs --follow backend
        mascope prod logs --tail 50 postgres
    """
    args = ["logs", "--tail", str(tail)]
    if follow:
        args.append("--follow")
    if service:
        args.append(service)
    _run_compose(args)


@prod_app.command()
def restart(
    service: Annotated[
        Optional[str],
        typer.Argument(
            help="Service name to restart. Restarts all services if omitted."
        ),
    ] = None,
) -> None:
    """
    Restart production containers.

    Runs `docker compose restart`, optionally scoped to a single service.

    \b
    Examples:
        mascope prod restart
        mascope prod restart postgres
        mascope prod restart backend
    """
    args = ["restart"]
    if service:
        args.append(service)
    _run_compose(args)


@prod_app.command(
    name="docker",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def docker_passthrough(ctx: typer.Context) -> None:
    """
    Pass arbitrary arguments directly to docker compose.

    Escape hatch for compose operations not covered by the explicit subcommands.
    All arguments after `docker` are forwarded verbatim to
    `docker compose --file <compose_path>`, with production environment
    variables injected.

    \b
    Examples:
        mascope prod docker exec -it postgres bash
        mascope prod docker pull
        mascope prod docker config
        mascope prod docker top backend
    """
    if not ctx.args:
        runtime.logger.error(
            "No arguments provided — usage: mascope prod docker <compose-args>"
        )
        raise typer.Exit(1)
    _run_compose(ctx.args)
