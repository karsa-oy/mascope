import os
import tomllib
from pydantic import BaseModel
from typing import Literal, List, Optional


# PYDANTIC MODELS

# Note: all relative paths like `./foo/bar` are resolved relative
# to the runtime environment active, which defaults to
#    $MASCOPE_PATH/runtime/env/default


class MascopeMetaConfig(BaseModel):
    """
    Global configuration options shared across all Mascope modules.
    """

    log_level: Optional[
        Literal["trace", "debug", "info", "success", "warning", "error", "critical"]
    ] = None  # global log level to print to terminal at
    description: str = "Mascope configuration"  # Description for `mascope env list`
    api_port: int = 8090  # API port
    filestore: str = r"./filestore"  # filestore path


class MascopeModuleConfig(BaseModel):
    """
    Base class for module-specific configuration; every Mascope module
    shares these configuration options.
    """

    name: str  # name of the module, e.g. 'backend'
    tags: Optional[List[str]] = []  # module groups to which the module should belong *
    pkg_path: Optional[str] = None  # the path to the Poetry or NPM package, if any
    log_path: Optional[str] = "./logs"  # path where to print log files
    log_level: Optional[
        Literal["trace", "debug", "info", "success", "warning", "error", "critical"]
    ] = None  # module log level to print to terminal at
    install: Optional[str] = None  # command to install the module, if any
    uninstall: Optional[str] = None  # commmand to uninstall the module, if any
    run: Optional[str] = None  # command to run the module, if any

    # * module groups allow you to easily run multiple modules.
    # For example, a common scenario is testing TOF acquisition
    # workflows. In `runtime/env/default/base.mascope.toml` we
    # have configured the `backend`, `frontend`, `tof_agent`,
    # and `file_converter` modules with the `tof` tag. This
    # means you can run `mascope dev run tof` and it will spin
    # up all of the services.


class MascopeBackendConfig(MascopeModuleConfig):
    """
    Backend module specific configuration options
    """

    database: str = r"./database"  # path to the database folder
    filestreams: str = r"./filestreams"  # path to the file streams folder


class MascopeFileConverterConfig(MascopeModuleConfig):
    """
    File converter module specific configuration options
    """

    server: str = r"backend"  # production host URL; the default works in our docker compose network
    source: str = r"./filestreams"  # folder to monitor for files to convert
    raw_threads: int = 2  # number of threads for converting Orbitrap files
    h5_threads: int = 2  # number of threads for converting Tof files
    interval: int = 3  # polling interval (s) when checking the file system


class MascopeTofAgentConfig(MascopeModuleConfig):
    """
    Tof Agent module specific configuration options
    """

    host: str  # URL of the backend
    source: str  # folder to monitor in the instrument machine
    target: str  # folder to transfer samples to in the server


class MascopeFileMoverConfig(MascopeModuleConfig):
    """
    File Mover module specific configuration options
    """

    mask: str = "*.raw"  # file pattern to look for
    timeout: int = 10  # timeout (s) for a file transfer operation
    source: str  # folder to monitor in the instrument machine
    target: str  # folder to transfer samples to in the server


class MascopeFrontendConfig(MascopeModuleConfig):
    """
    Frontend module specific configuration options
    """

    pass


class MascopeNotebooksConfig(MascopeModuleConfig):
    """
    Notebook module specific configuration options
    """

    pass


class MascopeCliConfig(MascopeModuleConfig):
    """
    Cli module specific configuration options
    """

    pass


class MascopeStandardLibConfig(MascopeModuleConfig):
    """
    Standard Library module specific configuration options
    """

    pass


class MascopeHardwareLibConfig(MascopeModuleConfig):
    """
    Hardware Library module specific configuration options
    """

    tofwerk_dll: Literal["Auto", "Linux", "Windows", "Darwin"] = "Auto"  # *
    # * Which TofWerk DLLs to use in the hardware library
    # Defaults to automatically resolving the platform.


class MascopeApiLibConfig(MascopeModuleConfig):
    """
    API Library module specific configuration options
    """

    pass


class MascopeRuntimeConfig(BaseModel):
    """
    The Mascope runtime configuration

    Includes the meta configuration, as well as all module
    configuration objects.
    """

    # global
    meta: MascopeMetaConfig
    # services
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


# UTILITY FUNCTIONS


def resolve_path(base_path: str, value: any) -> any:
    """
    Resolve relative paths using some base path.

    Only applies to strings starting with ./
    Other values are returned unmodified.

    :param base_path: the path relative to which to resolve
    :param value: the value to resolve, which may be a path string
    :return: resolved path or unchanged value
    """
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


def resolve_paths(root_path: str, env_path: str, config: dict) -> dict:
    """
    Iterate through a `config` dictionary, resolving paths.
    A resolved config dictionary is returned.

    The key "pkg_path" is resolved against MASCOPE_PATH - passed
    as the `root_path` argument. Meanwhile other relative path
    declarations are resolved against the currently active
    environment path, passed as `env_path`.

    :param root_path: the root MASCOPE_PATH
    :param env_path: the active runtime environment path
    :param config: the configuration for which to resolve paths
    :return: resolved configuration dictionary
    """
    new_config = {}
    for key, value in config.items():
        if isinstance(value, dict):
            # recurse for subconfigs
            new_config[key] = resolve_paths(root_path, env_path, value)
        else:
            # resolve paths for other values
            if key == "pkg_path":
                # package path is resolve against MASCOPE_PATH
                new_config[key] = resolve_path(root_path, value)
            else:
                # other paths are resolved against the runtime env
                new_config[key] = resolve_path(env_path, value)
    return new_config


def resolve_log_levels(config: dict, fallback: str = "info") -> dict:
    """
    Resolve log levels in a `config` dictionary using explicitly
    set configuration values, the CLI option passed through an env
    var, and a default, passed though the `fallback` argument.

    The order of precedence is:
      1. CLI option (--log-level debug / -l info)
      2. Module-specific config (log_level = "warning" in [backend])
      3. Global configuration (og_level = "critical" in [meta])
      4. The fallback (argument to this function)

    :param config: the configuration dictionary
    :param fallback: the fallback level if resolution fails
    :return: configuration dictionary with resolved log levels
    """
    new_config = {}
    meta = config.get("meta")
    meta_log_level = meta.get("log_level") if meta else None
    cli_env_var = os.environ.get("MASCOPE_LOGLEVEL")
    cli_log_level = cli_env_var.lower() if cli_env_var else None
    for sub_key, sub_config in config.items():
        # init subconfig
        new_config[sub_key] = config[sub_key]
        # resolve log levels
        config_log_level = sub_config.get("log_level")
        new_config[sub_key]["log_level"] = (
            cli_log_level  # cli overrides all
            or config_log_level  # otherwise use module level
            or meta_log_level  # otherwise use the meta level
            or fallback  # and worst case fall back to info
        )
    return new_config


def build_config(
    root_path: str, env_path: str, layers: List[str]
) -> MascopeRuntimeConfig:
    """
    Load a set of configuration `layers` (base, dev or prod),
    and overlay them such that each layer overrides properties
    set by the previous one. Then resolve relative paths and
    log levels using the `root_path` (MASCOPE_PATH) and the
    `env_path` (path to the environment).

    :param root_path: the root MASCOPE_PATH
    :param env_path: the active runtime environment path
    :param layers: list of config file paths to overlay
    :return: resolved and validated config Pydantic model
    """
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
                    config[module_key] = {
                        "name": module,  # pass the module name
                        **config[module_key],  # inherit previous layer
                        **module_overlay,  # override with overlay
                    }
    # resolve relative paths to absolute
    config = resolve_paths(root_path, env_path, config)
    # resolve log level based on config and cli args
    config = resolve_log_levels(config)
    # return validate model
    return MascopeRuntimeConfig(**config)
