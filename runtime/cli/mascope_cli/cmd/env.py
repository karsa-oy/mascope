import typer
import rich
from shutil import copytree
import tomllib, os, zipfile
from typing import Optional, Annotated

from rich.pretty import pprint
from rich.console import Console
from rich.table import Table

from mascope_cli.runtime import runtime

from mascope_runtime import MascopeRuntimeModule

pretty = lambda obj: pprint(obj, indent_guides=False, expand_all=True)

env_app = typer.Typer()


@env_app.callback()
def main():
    """
    Manage your mascope runtime environments
    """


@env_app.command()
def list():
    """
    List available envs

    Envs are stored in your `runtime/env` directory.
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
def activate(env: str):
    """
    Activate an env
    """
    runtime.state.env = env
    runtime.logger.info(f"Mascope env set to '{env}'")


@env_app.command()
def default():
    """
    Revert to the default env
    """
    runtime.state.env = "default"


# BROKEN - TODO: FIX
@env_app.command()
def copy(
    source: Annotated[str, typer.Argument()],
    target: Annotated[Optional[str], typer.Argument()] = None,
):
    """
    Copy a runtime
    """
    target = target or f"{source}_copy"
    source_path = os.path.join(runtime.state.root_path, "runtime", "env", source)
    target_path = os.path.join(runtime.state.root_path, "runtime", "env", target)

    def log(path, names):
        runtime.logger.info("Copying %s" % path.replace(source_path, ""))
        return []

    copytree(source_path, target_path, dirs_exist_ok=True, ignore=log)

# BROKEN - TODO: FIX
@env_app.command()
def export(
    env: Annotated[str, typer.Argument()],
    target: Annotated[Optional[str], typer.Argument()] = None,
):
    """
    Export a runtime to a zip archive
    """
    source_path = os.path.join(runtime.state.root_path, "runtime", "env", env)
    target_path = target or f"./{env}.mascope.zip"
    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as f:
        for root, _, files in os.walk(source_path):
            for file in files:
                f.write(
                    os.path.join(root, file),
                    os.path.relpath(
                        os.path.join(root, file), os.path.join(source_path, "..")
                    ),
                )
