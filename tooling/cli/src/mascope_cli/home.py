"""
Mascope runtime home resolution.

The "runtime home" is the directory the CLI (and the containers it launches)
treat as MASCOPE_PATH: it holds the config TOML layers, the compose files,
and `.runtime/` (state, secrets, database volumes, envs). In the monorepo it
is the checkout itself; for a pip-installed CLI it is a per-user data
directory created by `mascope init`.

Resolution order: an explicit `MASCOPE_PATH` env var always wins; otherwise
the platform default home is used if it has been initialized.
"""

import os
from pathlib import Path


def default_home() -> Path:
    """
    Platform-specific default runtime home.

    :return: `%LOCALAPPDATA%/Mascope` on Windows, `~/.mascope` elsewhere.
    :rtype: Path
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "Mascope"
        return Path.home() / "AppData" / "Local" / "Mascope"
    return Path.home() / ".mascope"


def is_initialized(path: Path) -> bool:
    """
    Whether `path` is a usable runtime home.

    The first config layer is the marker: without `base.mascope.toml` the
    runtime cannot load a valid configuration at all.

    :param path: Candidate runtime home directory.
    :type path: Path
    :return: True if the directory has been initialized.
    :rtype: bool
    """
    return (path / "base.mascope.toml").is_file()
