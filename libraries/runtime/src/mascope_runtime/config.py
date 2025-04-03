from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from mascope_runtime import Runtime

import os
import tomllib
from pydantic import BaseModel
from typing import Literal

# PYDANTIC MODELS

# Note: all relative paths like `./foo/bar` are resolved relative
# to the runtime environment active, which defaults to
#    $MASCOPE_PATH/runtime/env/default

type LogLevel = Literal[
    "trace", "debug", "info", "success", "warning", "error", "critical"
]


class MetaConfig(BaseModel):
    """
    Global configuration options shared across all  modules.
    """

    log_level: LogLevel | None = None  # global log level to print to terminal at
    description: str = "Mascope configuration"  # Description for `mascope env list`
    api_port: int = 8090  # API port
    filestore: str = r"./filestore"  # filestore path


class ModuleConfig(BaseModel):
    """
    Base class for module-specific configuration; every  module
    shares these configuration options.
    """

    name: str  # name of the module, e.g. 'backend'
    color: str | None = "white"  # color for logging tag
    tags: list[str] | None = []  # module groups to which the module should belong *
    log_path: str | None = "./logs"  # path where to print log files
    log_level: LogLevel | None = None  # module log level to print to terminal at
    run: str | None = None  # command to run the module, if any

    # * module groups allow you to easily run multiple modules.
    # For example, a common scenario is testing TOF acquisition
    # workflows. For example, with the default `base.mascope.toml`
    # configuration, running `mascope dev run tof` will spin up
    # the backend, frontend, file-converter and tof-agent modules.


class BackendConfig(ModuleConfig):
    """
    Backend module specific configuration options
    """

    database: str = r"./database"  # path to the database folder
    filestreams: str = r"./filestreams"  # path to the file streams folder


class FileConverterConfig(ModuleConfig):
    """
    File converter module specific configuration options
    """

    server: str = (
        r"backend"  # production host URL; the default works in our docker compose network
    )
    source: str = r"./filestreams"  # folder to monitor for files to convert
    raw_threads: int = 2  # number of threads for converting Orbitrap files
    h5_threads: int = 2  # number of threads for converting Tof files
    interval: int = 3  # polling interval (s) when checking the file system


class TofAgentConfig(ModuleConfig):
    """
    Tof Agent module specific configuration options
    """

    host: str  # URL of the backend
    access_token: str  # API access token


class FileAgentConfig(ModuleConfig):
    """
    File Agent module specific configuration options
    """

    mask: str = "*.raw"  # file pattern to look for
    timeout: int = 10  # timeout (s) for a file transfer operation
    source: str  # folder to monitor in the instrument machine
    host: str  # URL of the backend
    access_token: str  # API access token


class DatetimeRange(BaseModel):
    min: str | None = None
    max: str | None = None


class SampleTableDefaults(BaseModel):
    columns: list[str] = ["sample_item_name", "index"]
    sort_field: str = "index"
    sort_order: Literal[1, -1] = 1


class FrontendConfig(ModuleConfig):
    """
    Frontend module specific configuration options
    """

    acquisition_filter: DatetimeRange | str | None = None
    sample_table_defaults: SampleTableDefaults = SampleTableDefaults()


class CliConfig(ModuleConfig):
    """
    Cli module specific configuration options
    """

    pass


class ChemistryLibConfig(ModuleConfig):
    """
    Standard Library module specific configuration options
    """

    pass


class FileLibConfig(ModuleConfig):
    """
    Standard Library module specific configuration options
    """

    pass


class SignalLibConfig(ModuleConfig):
    """
    Standard Library module specific configuration options
    """

    pass


class TofwerkLibConfig(ModuleConfig):
    """
    Hardware Library module specific configuration options
    """

    tofwerk_dll: Literal["Auto", "Linux", "Windows", "Darwin"] = "Auto"  # *
    # * Which TofWerk DLLs to use in the hardware library
    # Defaults to automatically resolving the platform.


class ThermoLibConfig(ModuleConfig):
    """
    Hardware Library module specific configuration options
    """

    pass


class SdkLibConfig(ModuleConfig):
    """
    API Library module specific configuration options
    """

    pass


class RuntimeConfig(BaseModel):
    """
    The  runtime configuration

    Includes the meta configuration, as well as all module
    configuration objects.
    """

    # global
    meta: MetaConfig
    # services
    backend: BackendConfig | None = None
    file_converter: FileConverterConfig | None = None
    tof_agent: TofAgentConfig | None = None
    file_agent: FileAgentConfig | None = None
    # clients
    frontend: FrontendConfig | None = None
    cli: CliConfig | None = None
    # libraries
    chemistry_lib: ChemistryLibConfig | None = None
    signal_lib: SignalLibConfig | None = None
    file_lib: FileLibConfig | None = None
    tofwerk_lib: TofwerkLibConfig | None = None
    thermo_lib: ThermoLibConfig | None = None
    sdk_lib: SdkLibConfig | None = None


class RuntimeConfigLoader:
    """
    Helper class to facilitate loading the configuration of
    the runtime.

    During initialization, the class loads mascope.toml files,
    combines them, resolves paths and log levels and validates
    all fields using a Pydantic model.

    The resulting validated configuration is exposed with
    the `config` property.

    This class is to be used with the `load_config` below.
    """

    _runtime: Runtime
    _raw: dict
    _resolved: RuntimeConfig

    def __init__(self, runtime: Runtime):
        """
        Initializes the runtime configuration:

         1. Depending on the runtime mode, load `dev.mascope.toml`
            or `prod.mascope.toml` from the runtime environment;
            missing values use defaults set in `base.mascope.toml`
            in the runtime library.
         2. Resolve relative paths into absolute paths, using the
            runtime environment path (except for package paths,
            which resolve relative to the Mascope root path).
         3. Resolve log level for each module, using CLI arguments,
            toml settings and defaults.
         4. Validate the resulting dictionary using the Pydantic
            model for the configuration.

        :param runtime: The parent runtime
        :type runtime: Runtime
        """
        self._runtime = runtime

        config = self._load_tomls()
        config = self._resolve_paths(config)
        config = self._resolve_loglevels(config)
        config = self._validate_options(config)
        self._resolved = config

    @property
    def runtime(self):
        """
        The main runtime context
        """
        return self._runtime

    @property
    def config(self):
        """
        The loaded and resolved config
        """
        return self._resolved

    def _load_tomls(self):
        """
        Over defaults from `base.mascope.toml` in the runtime
        library, with settings in either `dev.mascope.toml` or
        `prod.mascope.toml`, returning the result as a dict.

        :return: Raw config dictionary
        :rtype: dict
        """
        self.base = self.runtime.path("base.mascope.toml")
        self.path = self.runtime.env.path(f"./{self.runtime.mode}.mascope.toml")

        raw_config = {}
        for path in [self.base, self.path]:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    # apply overlay
                    overlay = tomllib.load(f)
                    for module, module_overlay in overlay.items():
                        module_key = module.replace("-", "_")
                        if module_key not in raw_config:
                            raw_config[module_key] = {}
                        raw_config[module_key] = {
                            "name": module,  # pass the module name
                            **raw_config[module_key],  # inherit previous layer
                            **module_overlay,  # override with overlay
                        }
        return raw_config

    def _resolve_paths(self, unresolved: any | None = None) -> None:
        """
        Iterates through an unresolved config or - when recursing -
        a subdict thereof. When encountering a path-like string value,
        it replaces relative paths with absolute paths. Resolution
        uses the runtime env path by default, except for package
        paths which are resolved relative to the runtime root path.

        :return: Resolved config dictionary
        :rtype: dict
        """
        resolved = {}
        for key, value in unresolved.items():
            if isinstance(value, dict):
                # recurse for subconfigs
                resolved[key] = self._resolve_paths(value)
            elif isinstance(value, str):
                # resolve relative paths
                if value.startswith("./"):
                    # resolve against env
                    resolved[key] = self.runtime.env.realpath(value)
                # keep non-relative paths as-is
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved

    def _resolve_loglevels(self, unresolved: dict, fallback: LogLevel = "info") -> None:
        """
        Iterates through the root level of the unresolved config,
        resolving log levels based on various inputs.

        :return: Resolved config dictionary
        :rtype: dict
        """

        resolved = {}
        meta = unresolved.get("meta")
        meta_log_level = meta.get("log_level") if meta else None
        cli_env_var = os.environ.get("MASCOPE_LOGLEVEL")
        cli_log_level = cli_env_var.lower() if cli_env_var else None
        for sub_key, sub_config in unresolved.items():
            # init subconfig
            resolved[sub_key] = unresolved[sub_key]
            # resolve log levels
            config_log_level = sub_config.get("log_level")
            resolved[sub_key]["log_level"] = (
                cli_log_level  # cli overrides all
                or config_log_level  # otherwise use module level
                or meta_log_level  # otherwise use the meta level
                or fallback  # and worst case fall back to info
            )
        return resolved

    def _validate_options(self, unvalidated: dict) -> None:
        """
        Validates the resolved but unvalidated config dict using
        the Pydantic model.

        :return: Validated configuration model
        :rtype: RuntimeConfig
        """
        return RuntimeConfig(**unvalidated)


def load_config(runtime: Runtime):
    """
    Init a runtime config loader using the runtime,
    and return the resolved and validated config.

    :param runtime: The runtime context
    :type runtime: Runtime
    :return: The runtime configuration
    :rtype: RuntimeConfig
    """
    loader = RuntimeConfigLoader(runtime)
    return loader.config
