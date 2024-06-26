import os
import typer
from typing import Optional

from rich.console import Console
from rich.table import Table

import mascope_runtime as runtime

from . import cmd, lib

mascope_path=os.environ['MASCOPE_PATH']

app = typer.Typer()

app.add_typer(cmd.dev, name="dev")
app.add_typer(cmd.config, name="config")

@app.callback()
def main(config: Optional[str] = None):
    """
    🔭 Mascope development CLI
    """
    runtime.state.config_temp = config

@app.command()
def pkgs(installable: bool = False, runnable: bool = False):
    """
    📦 List packages in the monorepo

    Use --installable to list packages installed by 'mascope dev install' and
    --runnable to list packages that can be run by 'mascope dev run'.
    """
    def show(pkg):
        conditions=[
            (pkg['install'] if installable else True),
            (pkg['run'] if runnable else True)
        ]
        return all(conditions)
    
    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Path", style="green", no_wrap=True)
    table.add_column("Install", style="magenta", no_wrap=True)
    table.add_column("Run", style="magenta", no_wrap=True)
    table.add_column("Color", style="cyan", no_wrap=True)
    for pkg in lib.pkgs:
        if show(pkg):
            pkg_path=os.path.join(mascope_path, *pkg['path'])
            table.add_row(pkg['name'], pkg_path, pkg['install'], pkg['run'], pkg['color'])
    console = Console()
    console.print(table)

@app.command()
def path():
    """
    📂 Prints your mascope path

    This information is stored in the MASCOPE_PATH enviroment variable
    and used by the CLI and application.
    """
    print(os.environ['MASCOPE_PATH'])