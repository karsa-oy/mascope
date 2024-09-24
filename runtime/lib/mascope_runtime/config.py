import os, tomllib
from pydantic import BaseModel
from typing import Literal, List, Optional


class MascopeMetaConfig(BaseModel):
    log_level: Optional[
        Literal["trace", "debug", "info", "success", "warning", "error", "critical"]
    ] = None
    description: str = "Mascope configuration"
    api_port: int = 8090
    filestore: str = r"./filestore"


class MascopeModule(BaseModel):
    name: str
    tags: Optional[List[str]] = []
    pkg_path: Optional[str] = None
    log_path: Optional[str] = "./logs"
    log_level: Optional[
        Literal["trace", "debug", "info", "success", "warning", "error", "critical"]
    ] = None
    install: Optional[str] = None
    uninstall: Optional[str] = None
    run: Optional[str] = None


class MascopeBackendConfig(MascopeModule):
    database: str = r"./database"
    filestreams: str = r"./filestreams"


class MascopeFileConverterConfig(MascopeModule):
    server: str = r"backend"
    source: str = r"./filestreams"
    raw_threads: int = 2
    h5_threads: int = 2
    interval: int = 3


class MascopeTofAgentConfig(MascopeModule):
    host: str
    source: str
    target: str


class MascopeFileMoverConfig(MascopeModule):
    mask: str = "*.raw"
    timeout: int = 10
    source: str
    target: str


class MascopeFrontendConfig(MascopeModule):
    pass


class MascopeNotebooksConfig(MascopeModule):
    pass


class MascopeCliConfig(MascopeModule):
    pass


class MascopeStandardLibConfig(MascopeModule):
    pass


class MascopeHardwareLibConfig(MascopeModule):
    tofwerk_dll: Literal["Auto", "Linux", "Windows", "Darwin"] = "Auto"


class MascopeApiLibConfig(MascopeModule):
    pass


class MascopeRuntimeConfig(BaseModel):
    meta: MascopeMetaConfig
    backend: Optional[MascopeBackendConfig] = None
    file_converter: Optional[MascopeFileConverterConfig] = None
    tof_agent: Optional[MascopeTofAgentConfig] = None
    file_mover: Optional[MascopeFileMoverConfig] = None
    # clients
    notebooks: Optional[MascopeNotebooksConfig] = None
    frontend: Optional[MascopeFrontendConfig] = None
    cli: Optional[MascopeCliConfig] = None
    # libraries
    standard_lib: Optional[MascopeStandardLibConfig] = None
    hardware_lib: Optional[MascopeHardwareLibConfig] = None
    api_lib: Optional[MascopeApiLibConfig] = None


def resolve_path(base_path, value):
    # only process strings
    if isinstance(value, str):
        # that are relative paths
        if value.startswith("./"):
            path = value
            # join relative to the base path:
            #   "./foo/bar" => "/base_path/foo/bar"
            joined_path = os.path.join(
                base_path,
                *path.replace("./", "").split("/"),
            )
            # resolve symlinks:
            real_path = os.path.realpath(joined_path)
            return real_path
    # return other values as is
    return value


def resolve_paths(root_path, env_path, config):
    new_config = {}
    for key, value in config.items():
        if isinstance(value, dict):
            # recurse for subconfig dictionaries
            new_config = resolve_paths(env_path, value)
        else:
            # resolve paths for other values
            if key == "pkg_path":
                # package path is resolve against MASCOPE_PATH
                new_config[key] = resolve_path(root_path, value)
            else:
                # other paths are resolved against the runtime env
                new_config[key] = resolve_path(env_path, value)
    return new_config


def build_config(root_path, env_path, layers):
    config = {}
    for layer in layers:
        layer_path = os.path.join(env_path, f"{layer}.mascope.toml")
        # apply config layers
        if os.path.exists(layer_path):
            with open(layer_path, "rb") as f:
                # apply overlay
                overlay = tomllib.load(f)
                for module, module_overlay in overlay.items():
                    module_key = module.replace("-", "_")
                    if not module_key in config:
                        config[module_key] = {}
                    module_config = resolve_paths(
                        root_path,
                        env_path,
                        {
                            "name": module,  # pass the module name
                            **config[module_key],  # inherit previous layer
                            **module_overlay,  # override with overlay
                        },  # and resolve path attributes
                    )
                    config[module_key] = module_config
    # return validate model
    return MascopeRuntimeConfig(**config)


def default_overlay(mode):
    return f"""
[meta]
log_level = 'info'
"""
