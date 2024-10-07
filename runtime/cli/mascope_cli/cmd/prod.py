import typer, os, json, platform, time

from typing import Optional, List
from typing_extensions import Annotated

from mascope_runtime import MascopeRuntimeModule

from . import lib

compose_path = os.path.join(
    *os.path.split(os.environ["MASCOPE_PATH"]), "docker-compose.yaml"
)
compose_cmd = f"docker compose --file '{compose_path}'"

prod_app = typer.Typer(add_help_option=False)

long_help = """
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
    """
    if len(args) == 1 and args[0] == "--help":
        print(long_help)
    runtime = MascopeRuntimeModule("frontend")
    runtime.state.mode = "prod"
    command = f"{compose_cmd} {' '.join(args)}"
    # timezone
    if platform.system() != "Windows":
        # On Unix, inherit OS timezone
        timezone = "/".join(time.tzname)
    else:
        # On Windows, use hardcoded timezone *
        timezone = "Europe/Helsinki"
    print("command:", command)
    print("timezone: ", timezone)
    lib.run(
        command=command,
        vars=dict(
            MASCOPE_ENV=runtime.env,
            MASCOPE_RUNTIME=json.dumps(
                {
                    "mode": runtime.mode,
                    "env": runtime.env,
                    "meta": runtime.meta.model_dump(),
                    "config": runtime.config.model_dump(),
                    "version": os.environ["MASCOPE_VERSION"],
                }
            ),
            MASCOPE_FILESTORE=runtime.meta.filestore,
            MASCOPE_TIMEZONE=timezone,
        ),
    )


# * Windows uses a different timezone system
# than Linux or MacOS; converting from the
# Windows format proved difficult, and our
# app is deployed on Linux anyway, so a
# hardcoded value was deemed "good enough"
# for now.
