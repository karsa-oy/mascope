"""
Internal implementation for `mascope env create`.

Handles creation of runtime environment directories locally and on remote
machines. Not a Typer module — contains no commands.

An environment is simply a named directory under `.runtime/env/`. Creating
one makes it visible to `mascope env list`, `mascope env use`, and the
`validate_env` check used by db commands.

Callers (`main.py`) are responsible for argument parsing, confirmation
prompts, and error reporting.
"""

import subprocess

from pathlib import Path

from mascope_cli.cmd.env._paths import (
    local_env_dir,
    remote_env_dir,
)
from mascope_cli.runtime import runtime


# --- Validation ---


def validate_env_name(name: str) -> None:
    """
    Validate a proposed environment name.

    Rules:
    - Must not be empty
    - Must not contain whitespace
    - Must not contain path separators (`/` or `\\`)

    :param name: Proposed environment name.
    :type name: str
    :raises ValueError: If the name violates any rule.
    """
    if not name or not name.strip():
        raise ValueError("Environment name must not be empty.")
    if any(c in name for c in (" ", "\t", "\n")):
        raise ValueError(f"Environment name '{name}' must not contain whitespace.")
    if "/" in name or "\\" in name:
        raise ValueError(f"Environment name '{name}' must not contain path separators.")


# --- Local creation ---


def create_env_local(env_name: str) -> Path:
    """
    Create a local runtime environment directory.

    The directory is created at `.runtime/env/{env_name}/` under
    `MASCOPE_PATH`. Raises if it already exists — callers should check
    with `env_exists_local` first and handle the confirmation flow.

    :param env_name: Name of the environment to create.
    :type env_name: str
    :return: Absolute path to the created directory.
    :rtype: Path
    :raises ValueError: If `env_name` fails validation.
    :raises FileExistsError: If the environment directory already exists.
    """
    validate_env_name(env_name)

    env_dir = local_env_dir(env_name)
    if env_dir.exists():
        raise FileExistsError(f"Environment '{env_name}' already exists at {env_dir}.")

    env_dir.mkdir(parents=True, exist_ok=False)
    runtime.logger.info(f"Created environment '{env_name}' at {env_dir}")
    return env_dir


# --- Remote creation ---


def create_env_remote(remote: str, env_name: str) -> None:
    """
    Create a runtime environment directory on a remote machine via SSH.

    Uses `mkdir -p` — no CLI dependency on the remote side. The path is
    constructed from `remote_env_dir` so the layout is consistent with
    the local structure.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param env_name: Name of the environment to create on the remote.
    :type env_name: str
    :raises ValueError: If `env_name` fails validation.
    :raises RuntimeError: If the SSH command fails.
    """
    validate_env_name(env_name)

    path = remote_env_dir(remote, env_name)
    result = subprocess.run(
        ["ssh", remote, "bash", "-l", "-c", f"'mkdir -p {path}'"],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create environment '{env_name}' on {remote} at {path}."
        )
    runtime.logger.info(f"Created environment '{env_name}' on {remote} at {path}")
