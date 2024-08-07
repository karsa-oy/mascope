from . import config, logger
from .state import state
from .modules import modules
from .exceptions import *
from .config import MascopeConfig

import tomllib, os, re

from rich import print
from rich.console import Console
from rich.table import Table

mascope_path = os.environ["MASCOPE_PATH"]
runtime_dir = os.path.join(mascope_path, "runtime")

if not mascope_path:
    raise MascopeMissingPathException()


def resolve():
    name = state.temp or state.default or "dev"
    path = os.path.join(runtime_dir, name)
    return {"name": name, "path": path}


def mount():
    runtime = resolve()
    return config.load(runtime)


def list():
    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Path", style="magenta", no_wrap=True)
    table.add_column("Status", style="cyan", no_wrap=True)
    all_entries = [
        {"name": name, "path": os.path.join(runtime_dir, name)}
        for name in os.listdir(runtime_dir)
    ]
    runtimes = [
        entry
        for entry in all_entries
        if (os.path.isdir(entry["path"]) and not entry["name"].startswith("."))
    ]
    active = resolve()
    for runtime in runtimes:
        config_path = os.path.join(runtime["path"], f"mascope.toml")
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
            default = "default" if runtime["name"] == state.default else None
            fallback = "fallback" if (runtime["name"] == "dev") else None
            status = default or fallback
            selected = "*" if runtime["name"] == active["name"] else ""
            table.add_row(
                runtime["name"] + selected,
                config["meta"]["description"] or "n/a",
                runtime["path"],
                status,
            )
    console = Console()
    console.print(table)
