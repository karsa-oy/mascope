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
from mascope_runtime import Runtime

from mascope_cli.cmd import lib
from mascope_cli.cmd.prod.db import prod_db_app
from mascope_cli.runtime import runtime

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
        # Linux anyway, so a hardcoded value is good enough for now.
        timezone = "Europe/Helsinki"

    return dict(
        MASCOPE_ENV=runtime.env.name,
        MASCOPE_RUNTIME=mascope_runtime,
        MASCOPE_FILESTORE=runtime.meta.filestore,
        MASCOPE_TIMEZONE=timezone,
        MASCOPE_DB_NAME=db_name,
        MASCOPE_DB_USER=db_cfg.user,
        MASCOPE_PATH=os.environ["MASCOPE_PATH"],
        # Forwarded explicitly so compose variable interpolation is always
        # satisfied — empty string when --log-level was not passed, which
        # compose treats as "no override" for the container environment.
        MASCOPE_LOGLEVEL=os.environ.get("MASCOPE_LOGLEVEL", ""),
        MASCOPE_DB_CONTAINER_NAME=db_cfg.get_postgres_container_name(mode=_MODE),
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

    Runs `docker compose up --detach` by default. Pass `--detach` to stream
    combined logs to the terminal until Ctrl+C.

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
    if not detach:
        args.append("--detach")
    # Without --detach, compose streams combined logs to terminal by default
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
