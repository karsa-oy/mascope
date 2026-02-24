"""
Production environment management commands.

Provides commands to run, monitor, and manage Mascope production services.
"""

import os
import platform
import time
from typing import Optional, List
from typing_extensions import Annotated
import typer

from mascope_runtime import Runtime

import mascope_cli.cmd.lib as lib

compose_path = os.path.join(
    *os.path.split(os.environ["MASCOPE_PATH"]), "docker-compose.yaml"
)

prod_app = typer.Typer(add_help_option=False)

LONG_HELP = """
Manage the mascope production environment

This command is a thin wrapper around docker compose. You can use any
of docker compose's subcommands, arguments and options, e.g.:

    mascope prod up --detach
    mascope prod down
    mascope prod logs --follow
    mascope prod build

What follows is the output `docker compose --help`:
"""


@prod_app.callback(
    invoke_without_command=True, context_settings={"ignore_unknown_options": True}
)
def main(args: Annotated[Optional[List[str]], typer.Argument()] = None) -> None:
    """
    Manage the mascope production environment

    This is a thin wrapper around `docker compose`, which resolves the
    docker compose file and sets a variety of environment variables
    to inject the runtime env and config, timezone and host paths into
    the containers.

    Because it is a thin wrapper, it exposes the full compose CLI API:
    you can run any docker compose subcommand in almost exactly the
    same way as you can normally.

    Note: this docstring is not actually show in the help, unlike usual
    commands in the CLI. Instead, we print the `LONG_HELP` (see above)
    and then print `docker compose --help`.
    """
    if len(args) == 1 and args[0] == "--help":
        print(LONG_HELP)

    runtime = Runtime("frontend")
    runtime.state.mode = "prod"

    db_cfg = runtime.full_config.backend.database
    backend_cfg = runtime.full_config.backend
    file_converter_cfg = runtime.full_config.file_converter
    frontend_cfg = runtime.full_config.frontend
    redis_cfg = runtime.full_config.backend.redis

    db_name = db_cfg.get_postgres_database_name(env_name=runtime.env.name)

    command = f"docker compose --file '{compose_path}' {' '.join(args)}"

    # timezone
    if platform.system() != "Windows":
        # On Unix, inherit OS timezone
        timezone = "/".join(time.tzname)
    else:
        # On Windows, use hardcoded timezone *
        timezone = "Europe/Helsinki"

    print("command:", command)
    print("timezone: ", timezone)
    print("database:", db_name)

    lib.run(
        command=command,
        vars=dict(
            MASCOPE_ENV=runtime.env.name,
            MASCOPE_RUNTIME=runtime.module.to_json(),
            MASCOPE_FILESTORE=runtime.meta.filestore,
            MASCOPE_TIMEZONE=timezone,
            MASCOPE_DB_NAME=db_name,
            MASCOPE_DB_USER=db_cfg.user,
            MASCOPE_PATH=os.environ["MASCOPE_PATH"],
            # Container names injection
            MASCOPE_DB_CONTAINER_NAME=db_cfg.get_postgres_container_name(mode="prod"),
            MASCOPE_REDIS_CONTAINER_NAME=redis_cfg.get_redis_container_name(
                mode="prod"
            ),
            MASCOPE_BACKEND_CONTAINER_NAME=backend_cfg.get_backend_container_name(
                mode="prod"
            ),
            MASCOPE_FILE_CONVERTER_CONTAINER_NAME=file_converter_cfg.get_file_converter_container_name(
                mode="prod"
            ),
            MASCOPE_FRONTEND_CONTAINER_NAME=frontend_cfg.get_frontend_container_name(
                mode="prod"
            ),
        ),
    )


# * Windows uses a different timezone system
# than Linux or MacOS; converting from the
# Windows format proved difficult, and our
# app is deployed on Linux anyway, so a
# hardcoded value was deemed "good enough"
# for now.
