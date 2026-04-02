# import type hint w/o circular import error
from __future__ import annotations

import typing


if typing.TYPE_CHECKING:
    from mascope_runtime import Runtime

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
        """
        Initializes the runtime module interface.

        :param name: The name of the runtime module
        :type name: str
        :param runtime: The parent runtime context
        :type runtime: Runtime
        """
        self.name = name
        self._runtime = runtime

    @property
    def runtime(self) -> Runtime:
        """
        The parent runtime context
        """
        return self._runtime

    @property
    def config(self) -> ModuleConfig:
        """
        The runtime module's local configuration
        """
        return getattr(self.runtime._full_config, self.name.replace("-", "_"))

    def to_dict(self):
        """
        Serializes the runtime module context as a dictionary

        :return: A dictionary with module runtime information
        :rtype: dict
        """
        return {
            "config": self.config.model_dump(),
            "mode": self.runtime.mode,
            "env": self.runtime.env.name,
            "meta": self.runtime.meta.model_dump(),
            "version": self.runtime.version,
        }

    def to_json(self):
        """
        Serializes the runtime module context as a JSON string

        :return: A JSON string with module runtime information
        :rtype: str
        """
        return json.dumps(self.to_dict())
