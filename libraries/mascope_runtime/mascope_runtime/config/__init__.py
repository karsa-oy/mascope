import os, tomllib

from .model import *
from .exceptions import MascopeConfigNotFoundException


mascope_path = os.environ["MASCOPE_PATH"]
runtime_dir = os.path.join(mascope_path, "runtime")


def path(config_name):
    if config_name:
        return os.path.join(runtime_dir, f"mascope.toml")
    else:
        return None


def create_resolver(runtime):
    def resolver(path):
        if isinstance(path, str):
            if path.startswith("./"):
                return os.path.join(
                    mascope_path,
                    "runtime",
                    runtime["name"],
                    *path.replace("./", "").split("/"),
                )
        return path

    return resolver


def traverse(config, runtime):
    callback = create_resolver(runtime)
    for key, value in config.items():
        if isinstance(value, dict):
            traverse(config[key], runtime)
        else:
            config[key] = callback(value)


def load(runtime, mode="development"):
    config_path = os.path.join(runtime["path"], f"mascope.toml")
    # load configuration
    if os.path.exists(config_path):
        with open(config_path, "rb") as f:
            raw_config = tomllib.load(f)
            raw_config["meta"]["name"] = config_path.split(".")[1]
            raw_config["meta"]["path"] = os.environ["MASCOPE_PATH"]
            raw_config["meta"]["mode"] = mode
            config = MascopeConfig(**raw_config).model_dump()
            traverse(config, runtime)
            return MascopeConfig(**config)
    else:
        raise MascopeConfigNotFoundException(runtime)
