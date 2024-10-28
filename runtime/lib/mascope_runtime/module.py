from .config import MascopeMetaConfig, MascopeModuleConfig, build_config
from .state import MascopeRuntimeJsonState, MascopeRuntimeTempState
from .exceptions import MascopeConfigNotFoundException, MascopeMissingPathException
from .logger import config_logger

import os
from textwrap import dedent
from typing import Optional, List


class MascopeRuntimeModule:
    """
    A class representating an instance of the Mascope runtime
    within a specific runtime module. Each module has exactly
    one instance of its runtime module; this is enforced by a
    singleton pattern (see the `init` function in each module).

    The runtime module exposes the runtime lib and env for that
    specific module. This includes global runtime state and
    config as well as module-specific utilities.

    Global:
     - meta - global configuration from `mascope.toml` files
     - mode - whether in "dev" or "prod" mode
     - root_path - the current MASCOPE_PATH
     - env - the currently active runtime env name
     - env_path - path to the active runtime env
     - pkgs - all available module packages
     - modules - names of currently running modules

    Module-specific:
     - config - module-specific configuration from `mascope.toml` files
     - logger - module-specific logger

    The module bootstraps by:
        1. Resolving environment variables set by the
           install scripts and the CLI
        2. Building and validating the config from the
           `mascope.toml` files in the runtime env
        3. Configurating a loguru logger
    """

    name: str
    state: MascopeRuntimeJsonState | MascopeRuntimeTempState
    meta: MascopeMetaConfig
    config: MascopeModuleConfig
    pkgs: List[dict]

    _logger: any
    _root_path: str

    def __init__(
        self,
        name: str,
        env: Optional[str] = None,
        mode: Optional[str] = None,
        modules: Optional[List[str]] = None,
        path: Optional[str] = None,
    ) -> None:
        self.name = name
        resolved_path = path or os.environ.get("MASCOPE_PATH")
        if not resolved_path:
            raise MascopeMissingPathException()
        else:
            self._root_path = resolved_path
        if not (env or mode or modules):
            self.state = MascopeRuntimeJsonState(self._root_path)
        else:
            self.state = MascopeRuntimeTempState(env, mode, modules)
        self._load_config_()
        self._logger = config_logger(module=self)

    def _load_config_(self):
        def ensure_exists(layer):
            layer_path = os.path.join(
                self._root_path,
                "runtime",
                "env",
                self.state.env,
                f"{layer}.mascope.toml",
            )
            if not os.path.exists(layer_path):
                with open(layer_path, "w") as file:
                    file.write(
                        dedent(
                            f"""
                        # {layer} config overlay
                        # Overrides base configuration in `{layer}` mode. Refer
                        # to `base.mascope.toml` to see available options
                        """
                        ).strip()
                    )

        base_config_path = os.path.join(
            self._root_path,
            "runtime",
            "env",
            self.state.env,
            "base.mascope.toml",
        )
        if not os.path.exists(base_config_path):
            raise MascopeConfigNotFoundException(
                self.state.env, self.env_path, self.state.mode
            )
        ensure_exists("dev")
        dev_overlay = ["dev"] if self.state.mode == "dev" else []
        ensure_exists("prod")
        prod_overlay = ["prod"] if self.state.mode == "prod" else []
        full_config = build_config(
            self.root_path,
            self.env_path,
            [
                "base",  # common config
                *dev_overlay,  # dev config
                *prod_overlay,  # prod config
            ],
        )
        self.meta = full_config.meta
        self.config = getattr(full_config, self.name.replace("-", "_"))

        def get_pkgs(mod):
            return dict(
                (key, mod[key] if key in mod else None)
                for key in ("name", "tags", "pkg_path", "install", "uninstall", "run")
            )

        self.pkgs = [
            *map(
                get_pkgs,
                [
                    pkg
                    for pkg in full_config.model_dump().values()
                    if (pkg is not None and "name" in pkg and pkg["name"])
                ],
            )
        ]

    @property
    def logger(self):
        return self._logger

    @property
    def root_path(self):
        return self._root_path

    @property
    def env_path(self):
        return os.path.join(self._root_path, "runtime", "env", self.state.env)

    @property
    def env(self):
        return self.state.env

    @property
    def mode(self):
        return self.state.mode

    @property
    def modules(self):
        return self.state.modules
