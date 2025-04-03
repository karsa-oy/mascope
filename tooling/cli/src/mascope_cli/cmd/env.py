import typer
from typing import Annotated

from rich.console import Console
from rich.table import Table

from mascope_cli.runtime import runtime

from mascope_runtime import Runtime


env_app = typer.Typer()


@env_app.callback()
def main():
    """
    Manage your mascope runtime environments

    Runtime envs are folders in the `runtime/env` directory under your MASCOPE_PATH.
    They contain all the state needed to run Mascope apps and/or services, e.g. the
    database, file stores and file streaming folders.
    """


@env_app.command()
def list():
    """
    List available envs
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


def complete_env():
    return [e["name"] for e in runtime.env.list]


@env_app.command()
def use(
    env: Annotated[
        str,
        typer.Argument(
            help="The environment to activate",
            autocompletion=complete_env,
        ),
    ],
):
    """
    Activate an env, so that it is used in all subsequent commands
    """
    if env in [e["name"] for e in runtime.env.list]:
        runtime.state.env = env
        runtime.logger.info(f"Mascope env set to '{env}'")
    else:
        runtime.logger.error(f"No env named '{env}' was found")
