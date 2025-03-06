import os
import subprocess
import shlex
from loguru import logger

from .mode import RuntimeMode
from .state import RuntimeJsonState, RuntimeTempState
from .exceptions import MissingMascopePathException
from .env import RuntimeEnv
from .module import RuntimeModule
from .config import RuntimeConfig, MetaConfig, ModuleConfig, load_config
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

    state: RuntimeJsonState | RuntimeTempState
    env: RuntimeEnv
    module: RuntimeModule

    _path: str
    _version: str
    _full_config: RuntimeConfig

    def __init__(
        self,
        module: str,
        env: str | None = None,
        mode: RuntimeMode | None = None,
        path: str | None = None,
    ):
        """
        Initializes the primary runtime interface. Resolves the
        Mascope path and version, and instantiates the runtime
        state, environment, module, config and logging interfaces.

        :param module: The module in which the runtime is initialized.
        :type module: str
        :param env: The env to initialize the runtime with.
        :type env: str, Optional
        :param mode: The runtime mode ("dev" or "prod").
        :type mode: RuntimeMode, Optional
        :param path: A runtime path, overriding of MASCOPE_PATH
        :type path: str, Optional
        """
        # initialize attributes
        self._init_path(path=path)
        self._init_version()
        self._init_state(env=env, mode=mode)

        # initalize runtime
        self.env = RuntimeEnv(self)
        self.module = RuntimeModule(module, self)

        # load config
        self._full_config = load_config(self)

        # configure loguru global logger
        configure_logger(self)

    @property
    def mode(self) -> RuntimeMode:
        """
        The runtime mode ("dev" or "prod").
        """
        return self.state.mode

    @property
    def version(self) -> str:
        """
        The Mascope version string
        """
        return self._version

    @property
    def meta(self) -> MetaConfig:
        """
        The runtime's global configuration
        """
        return self._full_config.meta

    @property
    def config(self) -> ModuleConfig:
        """
        The runtime's local (module specific) configuration
        """
        return self.module.config

    @property
    def logger(self):
        """
        The runtime's local (module specific) configuration
        """
        return logger

    @property
    def modules(self):
        """
        List of available runtime modules, as dicts with
        various fields (documented below)
        """
        return [
            {
                key: mod.get(key)
                for key in (
                    "name",  # name of the module (e.g. 'backend')
                    "tags",  # tags for running as part of a group (e.g. 'file')
                    "pkg_path",  # path of the module's package
                    "install",  # command to install the module (optional)
                    "uninstall",  # command to uninstall the module (optional)
                    "run",  # command to run the module (optional)
                )
            }
            for mod in self._full_config.model_dump().values()
            if (mod is not None and "name" in mod and mod["name"])
        ]

    # PRIVATE METHODS

    def _init_path(self, path: str):
        """
        Resolve the mascope runtime path from the MASCOPE_PATH envvar
        and the provided 'path' argument. The path is persisted
        to self._path.

        :param path: A runtime path, overriding of MASCOPE_PATH
        :type path: str, Optional
        """
        resolved_path = path or os.environ.get("MASCOPE_PATH")
        if not resolved_path:
            raise MissingMascopePathException()
        else:
            self._path = resolved_path

    def _init_version(self):
        """
        Resolve the mascope version from the MASCOPE_VERSION envvar.
        The version is persisted to self._version.
        """
        self._version = os.environ.get("MASCOPE_VERSION")

    def _init_state(self, env: str | None = None, mode: RuntimeMode | None = None):
        """
        Initializes the mascope runtime state, which describes
        the currently active environment and runtime mode. If
        the runtime is provided with `env` or `mode` arguments,
        these are propagated, forcing a temporary state to be
        initialized rather than the persisted JSON state.

        :param env: The env to initialize the runtime with.
        :type env: str, Optional
        :param mode: The runtime mode ("dev" or "prod").
        :type mode: RuntimeMode, Optional
        """
        if env or mode:
            self.state = RuntimeTempState(env, mode)
        else:
            self.state = RuntimeJsonState(self._path)

    # PUBLIC METHODS

    def path(self, *args: list[str]) -> str:
        """
        Resolves the path relative to the runtime path.

        :param *args: A list of path segments or one string path in Unix notation
        :type arg: list[str], optional
        :return: Resolved path
        :rtype: str
        """
        if len(args) == 1 and "/" in args[0]:
            # resolve string paths like "./foo/bar"
            segments = args[0].replace("./", "").split("/")
        else:
            # treat arg list as-is
            segments = args
        return os.path.join(self._path, *segments)

    def realpath(self, *args: list[str]) -> str:
        """
        Resolves the path relative to the runtime path, resolving symlinks as well.

        :param *args: A list of path segments or one string path in Unix notation
        :type arg: list[str], optional
        :return: Resolved path
        :rtype: str
        """
        return os.path.realpath(self.path(*args))

    def secret(self, envvar: str, path: str, all_lines: bool = False) -> str:
        """
        Reads a secret, attempting to resolve the path from an `envvar`
        before falling back on a `path` argument. The contents of the
        file in the path are read and returned.

        If `all_lines` is True, it returns the full contents of the file;
        otherwise only the first line is returned.

        :param envvar: an environment variable containing the path of the secret file
        :type envvar: str
        :param path: a fallback path of the secret file
        :type path: str
        :param all_lines: Whether to return all lines or only the first.
        :type all_lines: bool
        :return: Secret file contents
        :rtype: str
        """
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

    def parse_version(self):
        """
        Construct a version string for the app from git history.
        The latest commit is used to construct the version, with
        the format differing depend on branch:

        In `master`:
          format: v{iso_date}-{short_commit_hash}
          example: v2024.09.03-d06bfef9

        In other branches:
          format: {branch}-v{iso_date}-{short_commit_hash}
          example: feature/new-stuff-v2024.09.03-d06bfef9
        """

        def exec(cmd: str):
            """
            Run a command in a subprocess and return the output
            """
            try:
                return (
                    subprocess.check_output(shlex.split(cmd), stderr=subprocess.DEVNULL)
                    .decode("utf-8")
                    .replace("\n", "")
                )
            except Exception:
                return None

        # construct a prefix from branch
        branch = exec("git rev-parse --abbrev-ref HEAD")
        if branch == "master":
            prefix = "v"
        else:
            prefix = f"{branch}-v"
        # get the latest commit date and short hash
        date_and_commit_hash = exec(
            'git log -1 --date=format:"%Y.%m.%d" --format="%ad-%h"'
        )
        # combine them to form the version string
        return (
            f"{prefix}{date_and_commit_hash}"
            if date_and_commit_hash
            else "unknown-version"
        )
