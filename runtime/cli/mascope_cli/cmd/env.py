import typer
from shutil import copytree
import os
import zipfile
from typing import Optional, Annotated

from rich.console import Console
from rich.table import Table

from mascope_cli.runtime import runtime

from mascope_runtime import MascopeRuntimeModule


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
    env_dir = os.path.join(runtime.root_path, "runtime", "env")
    all_entries = [
        {"name": name, "path": os.path.join(env_dir, name)}
        for name in os.listdir(env_dir)
    ]
    envs = [
        entry
        for entry in all_entries
        if (os.path.isdir(entry["path"]) and not entry["name"].startswith("."))
    ]
    for env in envs:
        env_runtime = MascopeRuntimeModule("cli", env=env["name"])
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


@env_app.command()
def activate(env: Annotated[str, typer.Argument(help="The environment to activate")]):
    """
    Activate an env, so that it is used in all subsequent commands
    """
    runtime.state.env = env
    runtime.logger.info(f"Mascope env set to '{env}'")


@env_app.command()
def default():
    """
    Activates the default env
    """
    runtime.state.env = "default"
