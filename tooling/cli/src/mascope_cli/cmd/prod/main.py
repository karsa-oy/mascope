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
import re
import time
from typing import Annotated, Optional

import typer

from mascope_cli.cmd import lib
from mascope_cli.cmd.prod.db import prod_db_app
from mascope_cli.pg.utils import check_data_dirs
from mascope_cli.runtime import runtime
from mascope_runtime import Runtime


_MODE = "prod"

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


def _compose_path() -> str:
    """
    Path of the production compose file under MASCOPE_PATH.

    :return: Absolute path to docker-compose.yaml.
    :rtype: str
    """
    return os.path.join(os.environ["MASCOPE_PATH"], "docker-compose.yaml")


def _deploy_version() -> str:
    """
    Resolve the image tag for pulling/running published production images.

    Published prod images exist only for master (``latest``) and release tags
    (``vX.Y.Z``) - never for the branch-derived dev build id - so this ignores
    the checked-out branch entirely: an explicit ``MASCOPE_VERSION`` pin wins;
    otherwise a semver tag at HEAD selects that release; otherwise ``latest``
    (the rolling master build).

    :return: The image tag to deploy.
    :rtype: str
    """
    if os.environ.get("_MASCOPE_VERSION_PINNED") == "1":
        return os.environ["MASCOPE_VERSION"]
    # Git only, not resolve_version: the CLI's own package version is a
    # calver (e.g. v2026.7.7) in a different series from the app's release
    # image tags (vX.Y.Z), so it must never be used as a deploy tag. A
    # pip-installed CLI without a pin deploys `latest`.
    version = runtime.parse_version()
    if re.fullmatch(r"v\d+\.\d+\.\d+", version):
        return version
    return "latest"


def _compose_env(building: bool = False) -> dict[str, str]:
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
        # Selects which image tag to pull/build (the compose `image:` field).
        # When building, use the current HEAD's version (branch-derived or
        # pinned) so the local build is tagged and displayed accordingly; when
        # pulling/running, use the deploy version (pin, release tag, or `latest`)
        # so a stray branch checkout never asks for an unpublished image tag.
        MASCOPE_VERSION=(
            os.environ["MASCOPE_VERSION"] if building else _deploy_version()
        ),
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
        # pg_dump --compress for the db_init pre-migration dump
        MASCOPE_DUMP_COMPRESSION=db_cfg.dump_compression,
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


def _run_compose(args: list[str], building: bool = False) -> None:
    """
    Invoke `docker compose` against the production compose file.

    Builds the full environment variable dict and delegates to `lib.run`.
    Mode override and config reload are handled in the callback — by the
    time any command calls this, config is already prod-scoped.

    :param args: docker compose subcommand and arguments,
                 e.g. `["up", "--detach"]` or `["logs", "--follow", "backend"]`.
    :type args: list[str]
    :param building: Whether this invocation builds images (vs. pulling/running).
                     Selects the current HEAD's version instead of the deploy
                     version for the compose `image:` tag.
    :type building: bool
    :raises typer.Exit: With docker compose's exit code when it fails, so
                        callers (CI in particular) can rely on the CLI's exit
                        status instead of scraping logs.
    """
    env_vars = _compose_env(building)
    command = f"docker compose --file '{_compose_path()}' {' '.join(args)}"

    runtime.logger.info(
        f"Database: {env_vars['MASCOPE_DB_NAME']}."
        f" Timezone: {env_vars['MASCOPE_TIMEZONE']}."
        f" Command: {command}"
    )

    result = lib.run(command=command, env_vars=env_vars)
    if result.returncode != 0:
        runtime.logger.error(
            f"docker compose exited with code {result.returncode} (command: {command})"
        )
        raise typer.Exit(result.returncode)


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
    # Check database bind-mount dirs before starting containers
    check_data_dirs(_MODE)
    args = ["up"]
    if rebuild:
        args.append("--build")
    if detach:
        args.append("--detach")
    # --build compiles the current HEAD (branch-derived version); a plain `up`
    # runs the deploy version (pin, release tag, or latest).
    _run_compose(args, building=rebuild)


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
    _run_compose(["build"], building=True)


@prod_app.command()
def update(
    version: Annotated[
        Optional[str],
        typer.Option(
            "--version",
            help="Release to update to: vX.Y.Z or 'latest'. Defaults to the "
            "MASCOPE_VERSION pin, or 'latest'.",
        ),
    ] = None,
) -> None:
    """
    Update the production stack to a newer release.

    Pulls the target release images and restarts the stack with them
    (`docker compose pull` followed by `up --detach`), then shows container
    status. Database migrations run automatically on startup — the db_init
    service takes a pre-migration dump into the backups directory first.
    Containers whose image did not change are left running, and a failed
    pull aborts before the running stack is touched.

    \b
    Examples:
        mascope prod update                        # follow the latest release
        mascope prod update --version v1.2.0       # move to a specific release
        MASCOPE_VERSION=v1.2.0 mascope prod update # same, via env pin
    """
    if version is not None:
        if version != "latest" and not re.fullmatch(r"v\d+\.\d+\.\d+", version):
            runtime.logger.error(
                f"Invalid release '{version}' - expected vX.Y.Z or 'latest'. "
                "For other image tags, pin via the MASCOPE_VERSION env var."
            )
            raise typer.Exit(1)
        # Same effect as an env pin: _deploy_version honors it for both the
        # pull and the restart.
        os.environ["MASCOPE_VERSION"] = version
        os.environ["_MASCOPE_VERSION_PINNED"] = "1"

    check_data_dirs(_MODE)
    target = _deploy_version()
    runtime.logger.info(f"Updating the production stack to '{target}'")
    _run_compose(["pull"])
    _run_compose(["up", "--detach"])
    _run_compose(["ps"])
    runtime.logger.success(f"Production stack updated to '{target}'")


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
