# import type hint w/o circular import error
from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from .instance import Runtime

import json

from .config import ModuleConfig


class RuntimeModule:
    """
    Represents a single runtime module, exposing the name
    and configuration of that module.
    """

    name: str

    _root: Runtime

    def __init__(self, name: str, root: Runtime) -> None:
        self.name = name
        self._root = root

    @property
    def root(self) -> Runtime:
        return self._root

    @property
    def config(self) -> ModuleConfig:
        return getattr(self.root._full_config, self.name.replace("-", "_"))

    def to_dict(self):
        return {
            "config": self.config.model_dump(),
            "mode": self.root.mode,
            "env": self.root.env.name,
            "meta": self.root.meta.model_dump(),
            "version": self.root.version,
        }

    def to_json(self):
        return json.dumps(self.to_dict())
