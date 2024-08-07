import os
import typer
from typing import Optional

from rich.console import Console
from rich.table import Table

import mascope_runtime

from . import cmd

mascope_path = os.environ["MASCOPE_PATH"]

app = typer.Typer()

app.add_typer(cmd.dev, name="dev")
app.add_typer(cmd.runtime, name="runtime")


@app.callback()
def main(runtime: Optional[str] = None):
    """
    Mascope development CLI
    """
    mascope_runtime.state.temp = runtime


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
    table.add_column("Color", style="cyan", no_wrap=True)
    for mod in mascope_runtime.modules:
        if show(mod):
            mod_path = os.path.join(mascope_path, *mod["path"])
            table.add_row(
                mod["name"], mod_path, mod["install"], mod["run"], mod["color"]
            )
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
