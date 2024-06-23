import typer, os
from typing import List, Dict, Annotated

from . import lib


cli=typer.Typer(help="🛠️ Manage your mascope CLI")

cli_pkg=next(pkg for pkg in lib.pkgs if pkg['name'] == 'cli')

@cli.command()
def update():
    """
    ✨ Update the CLI package in your system
    """
    update_cmd=f"cd {lib.repo_path}/scripts/cli && poetry build && pipx reinstall mascope_cli"
    lib.run(f'concurrently.cmd --names "mascope" "{update_cmd}" ')