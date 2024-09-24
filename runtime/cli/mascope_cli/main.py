from typing import Optional
import os
import typer

from typing_extensions import Annotated

from rich.console import Console
from rich.table import Table

from .runtime import runtime

from . import cmd

app = typer.Typer()

app.add_typer(cmd.env_app, name="env")
app.add_typer(cmd.dev_app, name="dev")
app.add_typer(cmd.prod_app, name="prod")


@app.callback()
def main(
    env: Annotated[Optional[str], typer.Option("--env", "-e")] = None,
    log_level: Annotated[Optional[str], typer.Option("--log-level", "-l")] = None,
    grep: Annotated[Optional[str], typer.Option("--log-grep", "-g")] = None,
):
    """
    Mascope development CLI
    """
    runtime.state.override("env", env)
    if log_level:
        os.environ["MASCOPE_LOGLEVEL"] = log_level.upper()
    if grep:
        os.environ["MASCOPE_LOGGREP"] = grep


@app.command()
def modules(installable: bool = False, runnable: bool = False):
    """
    List modules in the monorepo

    A 'module' may be a Python or NPM package or a service which is part of
    a package and can be independently run.

    Use --installable to list modules installed by 'mascope dev install' and
    --runnable to list modules that can be run by 'mascope dev run'.
    """

    def show(mod):
        conditions = [
            (mod["install"] if installable else True),
            (mod["run"] if runnable else True),
        ]
        return all(conditions)

    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Path", style="green", no_wrap=True)
    table.add_column("Install", style="magenta", no_wrap=True)
    table.add_column("Run", style="magenta", no_wrap=True)
    for mod in runtime.pkgs:
        if show(mod):
            table.add_row(mod["name"], mod["pkg_path"], mod["install"], mod["run"])
    console = Console()
    console.print(table)


@app.command()
def path():
    """
    Prints your mascope path

    This information is stored in the MASCOPE_PATH enviroment variable
    and used by the CLI and application.
    """
    print(os.environ["MASCOPE_PATH"])
