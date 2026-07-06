"""
Docker daemon checks shared across command groups.

Lives outside `mascope_cli.cmd` so that low-level helpers (`mascope_cli.pg`)
can use it without importing the command tree — `pg.utils` importing
`cmd.dev.docker` previously created a circular import that forced a strict
module load order in `cmd/__init__.py`.
"""

import subprocess


def is_docker_running() -> bool:
    """
    Check if Docker daemon is running.

    :return: True if Docker daemon is accessible, False otherwise
    :rtype: bool
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
