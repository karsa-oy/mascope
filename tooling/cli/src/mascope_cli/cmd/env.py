import typer
from typing import Annotated
import subprocess
import os

from rich.console import Console
from rich.table import Table

from mascope_cli.runtime import runtime
import mascope_cli.cmd.lib as lib

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


@env_app.command()
def sync(
    source: Annotated[
        str,
        typer.Argument(
            help="Source environment, optionally in a remote [USER@HOST:]ENV",
        ),
    ],
    destination: Annotated[
        str,
        typer.Argument(
            help="Destination environment, optionally in a remote [USER@HOST:]ENV",
        ),
    ],
    skip_filestore: Annotated[
        bool | None,
        typer.Option(
            "--skip-filestore",
            "-s",
            help="Skip synchronizing the filestore",
        ),
    ] = False,
):
    """
    Sync a runtime env from source to destination using rsync

    Both source and destination can be local paths or remote locations in an rsync-like format (USER@HOST:ENV).
    This allows transferring runtime envs between machines or creating backups.

    Note that this can take a while (hours), especially for large environment and across
    the network. For quicker sync, you can skip the filestore by using the --skip-filestore
    flag, or -s for short.
    """

    flags = " ".join(
        [
            "--progress",  # show progress bar
            "--recursive",  # recurse into directories
            "--copy-links",  # copy symlinks as files
            "--keep-dirlinks",  # maintain synlinked dirs in destination
        ]
        + (
            ["--exclude 'filestore/*'"]  # skip filestore if specified
            if skip_filestore
            else []
        )
    )

    def resolve(target: str):
        if "@" in target:
            [remote, env] = target.split(":")
            path = subprocess.run(
                ["ssh", remote, "bash", "-c", "'echo $MASCOPE_PATH'"],
                capture_output=True,
                text=True,
            ).stdout.strip("\n")
            return f"{remote}:{path}/.runtime/env/{env}/"
        else:
            return runtime.path(".runtime", "env", f"{target}/")

    src = resolve(source)
    dest = resolve(destination)

    cmd = f"rsync {flags} {src} {dest}"

    runtime.logger.info(
        f"Syncing {src} -> {dest}" + (" (skipping filestore)" if skip_filestore else "")
    )
    runtime.logger.info(cmd)
    lib.run(cmd)
