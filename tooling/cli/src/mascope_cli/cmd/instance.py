"""
`mascope instance` — manage per-worktree dev-stack instances.

Instances let several checkouts on one machine run the app at once against a
shared Postgres/Redis (see :mod:`mascope_cli.instance`). This group inspects
and cleans up the slot registry; instances are created on demand by
`mascope dev run --instance`.
"""

import os
import shutil
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from mascope_cli import instance as inst_lib
from mascope_cli.runtime import runtime


instance_app = typer.Typer()


@instance_app.callback()
def main() -> None:
    """
    Manage per-worktree dev-stack instances.

    An instance binds this checkout to a slot, giving it a dedicated env
    (``mascope_<env>`` database + filestore) and app ports so it can run
    alongside other worktrees. Create one with `mascope dev run --instance`.
    """


@instance_app.command(name="list")
def list_instances() -> None:
    """List allocated instances (slot, env, ports, worktree)."""
    instances = inst_lib.list_instances()
    if not instances:
        runtime.logger.info(
            "No instances allocated. Run `mascope dev run --instance` in a worktree."
        )
        return

    current = inst_lib.worktree_key()
    table = Table()
    table.add_column("", style="cyan", no_wrap=True)
    table.add_column("Slot", style="cyan", no_wrap=True)
    table.add_column("Env", style="green", no_wrap=True)
    table.add_column("Backend", style="magenta", no_wrap=True)
    table.add_column("Frontend", style="magenta", no_wrap=True)
    table.add_column("Worktree", style="white")
    for i in instances:
        table.add_row(
            "*" if i.worktree == current else "",
            str(i.slot),
            i.env,
            str(i.api_port),
            str(i.frontend_port),
            i.worktree,
        )
    Console().print(table)


@instance_app.command()
def show(
    export: Annotated[
        bool,
        typer.Option(
            "--export",
            help='Print shell exports for `eval "$(mascope instance show --export)"`',
        ),
    ] = False,
) -> None:
    """
    Show (allocating if needed) this worktree's instance.

    With ``--export``, print the env vars to activate it in a shell, so tools
    other than `mascope dev run` can target the same env and ports.
    """
    inst = inst_lib.resolve_or_allocate()

    if export:
        # Plain stdout (not the logger) so it is safe to eval.
        print(f"export MASCOPE_ENV={inst.env}")
        print(f"export MASCOPE_API_PORT={inst.api_port}")
        print(f"export MASCOPE_FRONTEND_PORT={inst.frontend_port}")
        return

    # Primary command output goes through rich (not the diagnostic logger),
    # so it renders cleanly when captured/piped, including on Windows consoles.
    console = Console()
    console.print(f"[cyan]Slot:[/]      {inst.slot}")
    console.print(f"[cyan]Env:[/]       {inst.env}")
    console.print(f"[cyan]Backend:[/]   http://localhost:{inst.api_port}")
    console.print(f"[cyan]Frontend:[/]  http://localhost:{inst.frontend_port}")
    console.print(f"[cyan]Worktree:[/]  {inst.worktree}")


@instance_app.command()
def rm(
    env: Annotated[
        Optional[str],
        typer.Argument(
            help="Env of the instance to release. Defaults to this worktree's instance.",
        ),
    ] = None,
    purge: Annotated[
        bool,
        typer.Option(
            "--purge",
            help="Also delete the env directory (filestore). The database is left intact.",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts."),
    ] = False,
) -> None:
    """
    Release an instance's slot so it can be reused.

    Frees the registry binding only; the ``mascope_<env>`` database is left in
    place (drop it with `mascope dev db drop --env <env>`). With ``--purge``,
    the env directory (filestore) is deleted too.
    """
    target_env = env
    if target_env is None:
        target_env = inst_lib.resolve_or_allocate().env

    released = inst_lib.release(target_env)
    if released is None:
        runtime.logger.warning(f"No instance found for env '{target_env}'")
        raise typer.Exit(1)

    runtime.logger.success(f"Released slot {released.slot} (env '{released.env}')")

    if purge:
        env_dir = Path(os.environ["MASCOPE_PATH"]) / ".runtime" / "env" / released.env
        if env_dir.exists():
            if not yes:
                typer.confirm(
                    f"Delete env directory {env_dir} (filestore data)?", abort=True
                )
            shutil.rmtree(env_dir, ignore_errors=True)
            runtime.logger.success(f"Deleted {env_dir}")
        runtime.logger.info(
            f"Database 'mascope_{released.env.replace('-', '_')}' left intact — "
            f"drop it with `mascope dev db drop --env {released.env}`"
        )
