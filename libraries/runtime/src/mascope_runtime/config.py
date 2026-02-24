"""
Runtime configuration models and loaders.

Defines Pydantic models for Mascope runtime configuration, including
global settings, module-specific options, and infrastructure dependencies.
Handles loading and validation of .mascope.toml configuration files with
three-layer overlay system.
"""

from __future__ import annotations
import os
import tomllib
from typing import Literal
import typing
from pydantic import BaseModel

if typing.TYPE_CHECKING:
    from mascope_runtime import Runtime


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


class DatabaseConfig(BaseModel):
    """
    Database configuration settings.

    Centralized configuration for PostgreSQL database connections, timeouts, and engine settings.
    """

    # Database type selector
    type: Literal["sqlite", "postgres"] = "sqlite"

    # Storage paths (relative to runtime env)
    data_dir: str = "./database"  # SQLite only: env./database/mascope.v43.db

    # PostgreSQL connection settings
    host: str = "localhost"
    port: int = 5432
    database: str = "mascope"  # Base name - actual will be mascope_{env}
    user: str = "mascope_user"  # password loaded via secret

    # Container settings (PostgreSQL only)
    container_name: str = "postgres"  # base name

    # Connection timeout
    connection_timeout: int = 30  # How long to wait when database is locked

    # SQLAlchemy engine settings
    pool_size: int = 5  # Base pool size - max persistent connections kept open
    max_overflow: int = (
        10  # Additional connections allowed beyond pool_size when needed
    )
    pool_timeout: int = 60  # Seconds to wait for available connection before timeout
    pool_pre_ping: bool = True  # Check connection liveness before using from pool
    expire_on_commit: bool = False  # Keep objects loaded after commit

    def get_sqlite_path(self, version: int) -> str:
        """Get full path to SQLite database file."""
        return os.path.join(self.data_dir, f"mascope.v{version}.db")

    def get_sqlite_url(self, version: int) -> str:
        """
        Build SQLite async URL (aiosqlite driver).

        :param version: Database schema version
        :return: SQLite async connection URL
        """
        return f"sqlite+aiosqlite:///{self.get_sqlite_path(version)}"

    def get_sqlite_url_sync(self, version: int) -> str:
        """
        Build SQLite sync URL (sqlite3 driver).

        Used by Alembic for migrations.

        :param version: Database schema version
        :return: SQLite sync connection URL
        """
        return f"sqlite:///{self.get_sqlite_path(version)}"

    def get_connect_args(self) -> dict:
        """Get database-specific connect_args for engine."""
        if self.type == "sqlite":
            return {"timeout": self.connection_timeout}
        return {}

    def get_postgres_container_name(self, mode: str) -> str:
        """
        Get mode-qualified postgres container name.

        :param mode: Runtime mode ('dev'/'prod')
        :return: e.g. 'mascope_dev_postgres', 'mascope_prod_postgres'
        """
        return f"mascope_{mode}_{self.container_name}"

    def get_postgres_database_name(self, env_name: str) -> str:
        """
        Get environment-specific database name.

        :param env_name: Runtime environment name (e.g., 'default', 'test-env')
        :return: Database name like 'mascope_default' or 'mascope_test_env'
        """
        # Sanitize env name for PostgreSQL (replace hyphens with underscores)
        safe_env = env_name.replace("-", "_").replace(" ", "_")
        return f"{self.database}_{safe_env}"

    def get_postgres_url(self, password: str, env_name: str) -> str:
        """
        Build PostgreSQL async URL (asyncpg driver).

        :param password: Database password
        :param env_name: Runtime environment name
        :return: PostgreSQL async connection URL
        """
        db_name = self.get_postgres_database_name(env_name)
        return f"postgresql+asyncpg://{self.user}:{password}@{self.host}:{self.port}/{db_name}"

    def get_postgres_url_sync(self, password: str, env_name: str) -> str:
        """
        Build PostgreSQL sync URL (psycopg2 driver) - used by Alembic.

        :param password: Database password
        :param env_name: Runtime environment name
        :return: PostgreSQL sync connection URL
        """
        db_name = self.get_postgres_database_name(env_name)
        return f"postgresql+psycopg2://{self.user}:{password}@{self.host}:{self.port}/{db_name}"


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


class RedisConfig(BaseModel):
    """
    Redis infrastructure configuration.
    """

    host: str = "localhost"
    port: int = 6379
    container_name: str = "redis"  # base name

    def get_redis_container_name(self, mode: str) -> str:
        """
        Get mode-qualified redis container name.

        :param mode: Runtime mode ('dev'/'prod')
        :return: e.g. 'mascope_dev_redis', 'mascope_prod_redis'
        """
        return f"mascope_{mode}_{self.container_name}"

    def get_redis_url(self) -> str:
        """Build Redis URL from host and port."""
        return f"redis://{self.host}:{self.port}"


class BackendConfig(ModuleConfig):
    """
    Backend module specific configuration options
    """

    container_name: str = "backend"  # base name
    database: DatabaseConfig = DatabaseConfig()
    filestreams: str = r"./filestreams"  # path to the file streams folder
    redis: RedisConfig = RedisConfig()
    workers: Literal["auto"] | int = "auto"  # uvicorn workers, auto -  half cpu cores

    def get_worker_count(self) -> int:
        """
        Resolve worker count, calculating from CPU cores if set to "auto".

        Rule of thumb for Mascope (mixed I/O + CPU workload):
        - auto: half CPU cores
        - explicit integer: use as-is

        Returns:
            int: Number of workers to use
        """
        if self.workers == "auto":
            cpu_cores = os.cpu_count() or 1
            return max(1, cpu_cores // 2)
        return self.workers

    def get_backend_container_name(self, mode: str) -> str:
        """
        Get mode-qualified backend container name.

        :param mode: Runtime mode ('dev'/'prod')
        :return: e.g. 'mascope_dev_backend', 'mascope_prod_backend'
        """
        return f"mascope_{mode}_{self.container_name}"


class FileConverterConfig(ModuleConfig):
    """
    File converter module specific configuration options
    """

    container_name: str = "file_converter"  # base name
    server: str = (
        r"backend"  # production host URL; the default works in our docker compose network
    )
    source: str = r"./filestreams"  # folder to monitor for files to convert
    raw_threads: int = 2  # number of threads for converting Orbitrap files
    h5_threads: int = 2  # number of threads for converting Tof files
    interval: int = 3  # polling interval (s) when checking the file system

    def get_file_converter_container_name(self, mode: str) -> str:
        """
        Get mode-qualified file converter container name.

        :param mode: Runtime mode ('dev'/'prod')
        :return: e.g. 'mascope_dev_file_converter', 'mascope_prod_file_converter'
        """
        return f"mascope_{mode}_{self.container_name}"


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
    container_name: str = "frontend"  # base name
    sample_table_defaults: SampleTableDefaults = SampleTableDefaults()

    def get_frontend_container_name(self, mode: str) -> str:
        """
        Get mode-qualified frontend container name.

        :param mode: Runtime mode ('dev'/'prod')
        :return: e.g. 'mascope_dev_frontend', 'mascope_prod_frontend'
        """
        return f"mascope_{mode}_{self.container_name}"


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


class MatchLibConfig(ModuleConfig):
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
    match_lib: MatchLibConfig | None = None
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

        1. Load config with 3-layer overlay:
            - base.mascope.toml - Shared defaults for all modes
            - {mode}.mascope.toml (runtime lib) - Mode-specific defaults
            - {mode}.mascope.toml (env dir, optional) - Env-specific overrides
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

    def _deep_merge(self, base: dict, overlay: dict) -> dict:
        """
        Deep merge overlay into base, preserving nested dicts.

        :param base: Base dictionary
        :param overlay: Overlay dictionary to merge
        :return: Merged dictionary
        """
        result = base.copy()
        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override with overlay value
                result[key] = value
        return result

    def _load_tomls(self) -> dict:
        """
        Load configuration with three-layer overlay system:

        1. base.mascope.toml (runtime library, git tracked)
           - Shared defaults for all modes
        2. {mode}.mascope.toml (runtime library, git tracked)
           - Mode-specific defaults (dev vs prod)
           - Overrides base settings
        3. {mode}.mascope.toml (env directory, not tracked)
           - Environment-specific overrides
           - Optional, for special cases only

        :return: Raw config dictionary
        :rtype: dict
        """
        # Layer 1: Base defaults (git tracked)
        base_path = self.runtime.path("base.mascope.toml")

        # Layer 2: Mode defaults from runtime library (git tracked)
        mode_base_path = self.runtime.path(f"{self.runtime.mode}.mascope.toml")

        # Layer 3: Env-specific overrides (not tracked, optional)
        mode_env_path = self.runtime.env.path(f"./{self.runtime.mode}.mascope.toml")

        # Debug output
        self.runtime.logger.trace("Config loading:")
        self.runtime.logger.trace(f"  Runtime env.name: {self.runtime.env.name}")
        self.runtime.logger.trace(f"  Runtime mode: {self.runtime.mode}")
        self.runtime.logger.trace(f"  Layer 1 (base): {base_path}")
        self.runtime.logger.trace(f"  Layer 2 (mode): {mode_base_path}")
        self.runtime.logger.trace(f"  Layer 3 (env):  {mode_env_path}")

        raw_config = {}
        # Apply layers in order: base → mode (lib) → mode (env)
        for path in [base_path, mode_base_path, mode_env_path]:
            if os.path.exists(path):
                self.runtime.logger.trace(f"  ✅ Loading: {path}")
                with open(path, "rb") as f:
                    # apply overlay
                    overlay = tomllib.load(f)
                    for module, module_overlay in overlay.items():
                        module_key = module.replace("-", "_")
                        if module_key not in raw_config:
                            raw_config[module_key] = {}

                        base_config = {"name": module, **raw_config[module_key]}
                        raw_config[module_key] = self._deep_merge(
                            base_config, module_overlay
                        )
            else:
                self.runtime.logger.trace(f"  ❌ Not found: {path}")

        return raw_config

    def _resolve_paths(self, unresolved: dict) -> dict:
        """
        Iterates through an unresolved config or - when recursing -
        a subdict thereof. When encountering a path-like string value,
        it replaces relative paths with absolute paths. Resolution
        uses the runtime env path by default, except for package
        paths which are resolved relative to the runtime root path.

        :param unresolved: Raw config dictionary with unresolved paths
        :type unresolved: dict
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
                    resolved_path = self.runtime.env.realpath(value)
                    resolved[key] = resolved_path

                    # Debug logging for important paths
                    if key in [
                        "filestore",
                        "database",
                        "log_path",
                        "source",
                        "data_dir",
                    ]:
                        self.runtime.logger.trace(
                            f"Path resolved: {key}: '{value}' → '{resolved_path}'"
                        )

                else:
                    # keep non-relative paths as-is
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved

    def _resolve_loglevels(self, unresolved: dict, fallback: LogLevel = "info") -> dict:
        """
        Iterates through the root level of the unresolved config,
        resolving log levels based on various inputs.

        :param unresolved: Config dictionary with unresolved log levels
        :type unresolved: dict
        :param fallback: Fallback log level if none specified (default: "info")
        :type fallback: LogLevel
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

    def _validate_options(self, unvalidated: dict) -> RuntimeConfig:
        """
        Validates the resolved but unvalidated config dict using
        the Pydantic model.

        :param unvalidated: Resolved config dictionary without validation
        :type unvalidated: dict
        :return: Validated configuration model
        :rtype: RuntimeConfig
        """
        return RuntimeConfig(**unvalidated)


def load_config(runtime: Runtime) -> RuntimeConfig:
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
