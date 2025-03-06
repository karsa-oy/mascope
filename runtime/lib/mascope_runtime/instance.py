import os
from loguru import logger

from .mode import RuntimeMode
from .state import RuntimeJsonState, RuntimeTempState
from .exceptions import MissingMascopePathException
from .options import RuntimeOptions
from .env import RuntimeEnv
from .module import RuntimeModule
from .config import MetaConfig, load_config
from .logger import configure_logger


class Runtime:
    """
    The main runtime instance, providing a localized interface
    to the Mascope runtime.

    Each service, library and tool - known collectively as
    'modules' - have their own runtime instance; they are
    distinguished by the 'module' string identifier passed
    to this class.

    The class provides access to global runtime interfaces like
    state, environment and meta configuration, as well as local
    runtime interfaces such as the module's own config.
    """

    options: RuntimeOptions
    state: RuntimeJsonState | RuntimeTempState
    env: RuntimeEnv
    module: RuntimeModule

    _path: str
    _version: str

    def __init__(self, module: str, **opts):
        # load options
        self.options = RuntimeOptions(**opts)

        # initialize attributes
        self.read_envvars()
        self.init_state()

        # initalize runtime
        self.env = RuntimeEnv(self)
        self.module = RuntimeModule(module, self)

        # load config
        self._full_config = load_config(self)

        # configure loguru global logger
        configure_logger(self)

    @property
    def mode(self) -> RuntimeMode:
        return self.state.mode

    @property
    def version(self) -> str:
        return self._version

    @property
    def meta(self) -> MetaConfig:
        return self._full_config.meta

    @property
    def config(self):
        return self.module.config

    @property
    def logger(self):
        return logger

    @property
    def modules(self):
        return [
            {
                key: mod.get(key)
                for key in (
                    "name",
                    "tags",
                    "pkg_path",
                    "install",
                    "uninstall",
                    "run",
                )
            }
            for mod in self._full_config.model_dump().values()
            if (mod is not None and "name" in mod and mod["name"])
        ]

    # METHODS

    def path(self, *args: list[str]) -> str:
        if len(args) == 1 and "/" in args[0]:
            # resolve string paths like "./foo/bar"
            segments = args[0].replace("./", "").split("/")
        else:
            # treat arg list as-is
            segments = args
        return os.path.join(self._path, *segments)

    def realpath(self, *args: list[str]) -> str:
        return os.path.realpath(self.path(*args))

    def read_envvars(self):
        resolved_path = self.options.path or os.environ.get("MASCOPE_PATH")
        if not resolved_path:
            raise MissingMascopePathException()
        else:
            self._path = resolved_path
        self._version = os.environ.get("MASCOPE_VERSION")

    def init_state(self):
        if self.options.env or self.options.mode:
            self.state = RuntimeTempState(self.options.env, self.options.mode)
        else:
            self.state = RuntimeJsonState(self._path)

    def secret(self, envvar: str, path: str, all_lines: bool = False) -> str:
        # construct paths to look in
        envvar_path = os.environ.get(envvar)
        root_path = self.path("secrets", path)
        # try to open each path
        for file_path in [envvar_path, root_path]:
            # ensure the path and file exist
            if file_path and os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    # if succesful, return the result
                    return (
                        "\n".join(f.readlines())  # all lines
                        if all_lines
                        else f.readlines()[0].replace("\n", "")  # first line
                    )
        # if no file was found, raise an error
        raise FileNotFoundError(
            f"Secret could not be found using env var {envvar} and path {path}"
        )
