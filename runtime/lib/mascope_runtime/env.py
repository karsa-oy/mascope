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
    def path(self) -> str:
        """
        The runtime environment path
        """
        return os.path.join(self._root.path, "runtime", "env", self.name)

    def resolve(self, path: str) -> any:
        """
        Resolve a path relative to the runtime environment;
        a path like ./foo/bar is transformed to a path like
        /my/mascope/runtime/env/myenv/foo/bar, if the
        $MASCOPE_PATH is set to /my/mascope.
        """
        # only process strings
        if not isinstance(path, str):
            raise ValueError("Path must be a string")
        # only resolve relative paths
        if path.startswith("./"):
            path = path
            # join relative to the base path:
            #   "./foo/bar" => "/base_path/foo/bar"
            joined_path = os.path.join(
                self.path,
                *path.replace("./", "").split("/"),
            )
            # resolve symlinks:
            real_path = os.path.realpath(joined_path)
            return real_path
        else:
            return path
