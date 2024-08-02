import tomllib, os, re

from rich import print
from rich.console import Console
from rich.table import Table

from ..state import state

from .exceptions import *
from .model import MascopeConfig

mascope_path = os.environ["MASCOPE_PATH"]
config_dir = os.path.join(mascope_path, "runtime", "configs")

if not mascope_path:
    raise MascopeMissingPathException()


def path(config_name):
    if config_name:
        return os.path.join(config_dir, f"mascope.{config_name}.toml")
    else:
        return None


def resolve_path(path):
    if isinstance(path, str):
        if path.startswith("./"):
            return os.path.join(mascope_path, *path.replace("./", "").split("/"))
    return path


def traverse(config, callback):
    for key, value in config.items():
        if isinstance(value, dict):
            traverse(config[key], callback)
        else:
            config[key] = callback(value)


def load(config_path):
    # load configuration
    with open(config_path, "rb") as f:
        raw_config = tomllib.load(f)
        raw_config["meta"]["name"] = config_path.split(".")[1]
        raw_config["meta"]["path"] = os.environ["MASCOPE_PATH"]
        config = MascopeConfig(**raw_config).model_dump()
        traverse(config, resolve_path)
        return MascopeConfig(**config)


def autoload():
    config_name = state.temp or state.default
    # helpers
    config_file = lambda name: (
        path(name) if (name and os.path.exists(path(name))) else None
    )
    # resolve config
    if config_name:
        selected_config_file = config_file(config_name)
        if not selected_config_file:
            raise MascopeConfigNotFoundException(config_dir, config_name)
    else:
        selected_config_file = config_file("prod") or config_file("dev")
        if not selected_config_file:
            raise MascopeConfigNotResolvedException(config_dir)
    # load config
    return load(selected_config_file)


def list():
    pattern = re.compile(r"^mascope\.[A-Za-z0-9_]+\.toml$")
    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("File", style="magenta", no_wrap=True)
    table.add_column("Status", style="cyan", no_wrap=True)
    configs = os.listdir(config_dir)
    not_active = not f"mascope.{state.default}.toml" in configs
    for conf in configs:
        if pattern.match(conf):
            with open(os.path.join(config_dir, conf), "rb") as f:
                config = tomllib.load(f)
                name = conf.split(".")[1]
                active = "active" if name == state.default else None
                default = (
                    "default"
                    if (
                        name == "prod"
                        or (name == "dev" and not "mascope.prod.toml" in configs)
                    )
                    else None
                )
                status = active or default
                selected = (
                    ("*" if (not_active and default) else None)
                    or ("*" if active else None)
                    or ""
                )
                table.add_row(
                    name + selected,
                    config["meta"]["description"] or "n/a",
                    conf,
                    status,
                )
    console = Console()
    console.print(table)
