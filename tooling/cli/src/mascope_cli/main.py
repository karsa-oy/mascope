"""
Mascope CLI entry point.

Defines the top-level `mascope` command group, shared options (env override,
log level, log grep), and the utility commands `modules`, `groups`, and `path`.
All environment-specific functionality is delegated to sub-apps under
`mascope_cli.cmd`.
"""

import os
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from mascope_cli import cmd
from mascope_cli.runtime import runtime


app = typer.Typer()

app.add_typer(cmd.env_app, name="env")
app.add_typer(cmd.demo_app, name="demo")
app.add_typer(cmd.dev_app, name="dev")
app.add_typer(cmd.prod_app, name="prod")
app.add_typer(cmd.logs_app, name="logs")
app.add_typer(cmd.backend_app, name="backend")
app.add_typer(cmd.agent_app, name="agent")
app.add_typer(cmd.cert_app, name="cert")
app.add_typer(cmd.test_app, name="test")


@app.callback()
def main(
    env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help="Override the active Mascope runtime env for the duration of the command",
        ),
    ] = None,
    log_level: Annotated[
        Optional[str],
        typer.Option(
            "--log-level", "-l", help="Set the log level shown in terminal logs"
        ),
    ] = None,
    log_grep: Annotated[
        Optional[str],
        typer.Option(
            "--log-grep",
            "-g",
            help="Highlight lines matching the grep pattern in the terminal logs",
        ),
    ] = None,
):
    """
    Mascope development CLI

    The `mascope` CLI offers a series of commands for managing development and
    production environments, as well as the database. A few top-level options
    are shared between dev and prod modes, but most functionality and options
    are delegated to the specific commands.

    \b
    Type `mascope <cmd> --help` to learn more about a specific command.
    """
    # Default the version from git, but let an explicitly-set MASCOPE_VERSION win
    # (e.g. pinning a release image for a prod deploy: MASCOPE_VERSION=v1.0.0).
    os.environ.setdefault("MASCOPE_VERSION", runtime.parse_version())

    # override active env with CLI option (null if not provided)
    runtime.state.override("env", env)

    # Set log level for terminal output. Always sync the env var so docker
    # compose never sees a stale value from a previous invocation.
    if log_level:
        os.environ["MASCOPE_LOGLEVEL"] = log_level.upper()
    elif "MASCOPE_LOGLEVEL" in os.environ:
        del os.environ["MASCOPE_LOGLEVEL"]

    # Set grep highlight pattern for terminal logs
    if log_grep:
        os.environ["MASCOPE_LOGGREP"] = log_grep
    elif "MASCOPE_LOGGREP" in os.environ:
        del os.environ["MASCOPE_LOGGREP"]


@app.command()
def modules(
    runnable: Annotated[
        Optional[bool],
        typer.Option(help="Only list modules that can be run with `mascope dev run`"),
    ] = False,
):
    """
    List modules in the monorepo

    A 'module' may be a Python or NPM package or a service which is part of
    a package and can be independently run.

    Use --installable to list modules installed by 'mascope dev install' and
    --runnable to list modules that can be run by 'mascope dev run'.
    """

    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Color", style="magenta", no_wrap=True)
    table.add_column("Command", style="magenta", no_wrap=True)
    for mod in runtime.modules:
        if mod["run"] if runnable else True:
            table.add_row(mod["name"], mod["color"], mod["run"])
    console = Console()
    console.print(table)


@app.command()
def groups():
    """
    List runtime groups in the monorepo

    A 'group' is a set of runtime modules that can be
    launched together with `mascope dev run <group_name>`.
    """

    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Modules", style="magenta", no_wrap=True)
    for group in runtime.groups:
        table.add_row(
            group["name"], ", ".join([mod["name"] for mod in group["modules"]])
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
