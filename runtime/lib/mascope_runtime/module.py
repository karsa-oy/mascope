# import type hint w/o circular import error
from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from .runtime import Runtime

import json

from .config import ModuleConfig


class RuntimeModule:
    """
    Represents a single runtime module, exposing the name
    and configuration of that module.
    """

    name: str

    _runtime: Runtime

    def __init__(self, name: str, runtime: Runtime) -> None:
        self.name = name
        self._runtime = runtime

    @property
    def runtime(self) -> Runtime:
        return self._runtime

    @property
    def config(self) -> ModuleConfig:
        return getattr(self.runtime._full_config, self.name.replace("-", "_"))

    def to_dict(self):
        return {
            "config": self.config.model_dump(),
            "mode": self.runtime.mode,
            "env": self.runtime.env.name,
            "meta": self.runtime.meta.model_dump(),
            "version": self.runtime.version,
        }

    def to_json(self):
        return json.dumps(self.to_dict())
