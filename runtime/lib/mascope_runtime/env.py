# import type hint w/o circular import error
from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from .instance import Runtime

import os


class RuntimeEnv:
    """
    An interface to the runtime environment, providing
    the name and path of the environment as well as a
    method for resolving paths relative to the env.
    """

    name: str

    _root: Runtime

    def __init__(self, root: Runtime):
        # init attributes
        self._root = root
        self.name = self.root.state.env

    @property
    def root(self) -> Runtime:
        return self._root

    @property
    def dir(self) -> str:
        return self.root.path("runtime", "env")

    @property
    def list(self) -> list[dict]:
        envdir = [
            {"name": name, "path": os.path.join(self.dir, name)}
            for name in os.listdir(self.dir)
        ]
        envs = [
            entry
            for entry in envdir
            if (os.path.isdir(entry["path"]) and not entry["name"].startswith("."))
        ]
        return envs

    # METHODS

    def path(self, *args: list[str]) -> str:
        if len(args) == 1 and "/" in args[0]:
            # resolve string paths like "./foo/bar"
            segments = args[0].replace("./", "").split("/")
        else:
            # treat arg list as-is
            segments = args
        return os.path.join(self.dir, self.name, *segments)

    def realpath(self, *args: list[str]) -> str:
        return os.path.realpath(self.path(*args))
