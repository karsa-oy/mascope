import typer
import rich
from shutil import copytree
import os, zipfile
from typing import Optional, Annotated


import mascope_runtime

pretty = lambda obj: rich.pretty.pprint(obj, indent_guides=False, expand_all=True)

runtime = typer.Typer()

mascope_path = os.environ["MASCOPE_PATH"]
runtime_dir = os.path.join(mascope_path, "runtime")

logger = mascope_runtime.logger.service("cli")


@runtime.callback()
def main():
    """
    Manage your mascope runtimes
    """


@runtime.command()
def list():
    """
    List available runtimes in your runtime directory
    """
    mascope_runtime.list()


@runtime.command()
def set(runtime: str):
    """
    Set the active runtime
    """
    mascope_runtime.state.default = runtime
    rich.print(f"Mascope runtime set to '{runtime}'")


@runtime.command()
def unset():
    """
    Unset the active runtime, defaulting to 'dev'
    """
    mascope_runtime.state.default = None


@runtime.command()
def show():
    """
    Show the active runtime's configuration
    """
    pretty(mascope_runtime.mount())


@runtime.command()
def copy(
    source: Annotated[str, typer.Argument()],
    target: Annotated[Optional[str], typer.Argument()],
):
    """
    Copy a runtime
    """
    target = target or f"{source}_copy"
    source_path = os.path.join(runtime_dir, source)
    target_path = os.path.join(runtime_dir, target)

    def log(path, names):
        logger.info("Copying %s" % path.replace(source_path, ""))
        return []

    copytree(source_path, target_path, dirs_exist_ok=True, ignore=log)


@runtime.command()
def export(
    runtime: Annotated[str, typer.Argument()],
    target: Annotated[Optional[str], typer.Argument()] = None,
):
    """
    Export a runtime to a zip archive
    """
    source_path = os.path.join(runtime_dir, runtime)
    target_path = target or f"./{runtime}.mascope.zip"
    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as f:
        for root, dirs, files in os.walk(source_path):
            for file in files:
                f.write(
                    os.path.join(root, file),
                    os.path.relpath(
                        os.path.join(root, file), os.path.join(source_path, "..")
                    ),
                )
