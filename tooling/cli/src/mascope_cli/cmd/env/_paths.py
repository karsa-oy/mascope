"""
Shared path and address utilities for `mascope env` commands.

Used by both `_sync.py` and `_create.py` to avoid duplication.
Contains no Typer commands — implementation only.
"""

import subprocess
from pathlib import Path, PurePosixPath

from mascope_cli.cmd.env._ssh import cygwin_bin, get_identity_args
from mascope_cli.runtime import runtime


def parse_address(address: str) -> tuple[str | None, str]:
    """
    Parse a sync address into `(remote, env_name)`.

    Accepts two formats:
    - `ENV`           — local environment, no remote
    - `USER@HOST:ENV` — remote environment

    :param address: Raw address string from CLI argument.
    :type address: str
    :return: `(remote, env_name)` where `remote` is `None` for local addresses.
    :rtype: tuple[str | None, str]
    :raises ValueError: If the address contains `@` but no `:` separator.
    """
    if "@" in address:
        if ":" not in address:
            raise ValueError(
                f"Invalid remote address '{address}': expected USER@HOST:ENV format."
            )
        remote, env_name = address.split(":", 1)
        return remote, env_name
    return None, address


def local_env_dir(env_name: str) -> Path:
    """
    Return the absolute local host path for a named environment directory.

    :param env_name: Name of the runtime environment.
    :type env_name: str
    :return: Absolute path to `.runtime/env/{env_name}/`.
    :rtype: Path
    """
    return Path(runtime.path(".runtime", "env", env_name))


def remote_env_dir(
    remote: str,
    env_name: str,
    control_args: list[str] | None = None,
) -> str:
    """
    Return the absolute POSIX path for a named environment directory on a
    remote machine.

    Queries `MASCOPE_PATH` via `mascope path` over SSH and constructs the
    path using `PurePosixPath` to guarantee forward slashes regardless of
    the local OS.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param env_name: Name of the runtime environment.
    :type env_name: str
    :param control_args: SSH multiplexing flags from `SshMux` to reuse an
                         existing ControlMaster connection. Pass `[]` or
                         `None` for a standalone connection.
    :type control_args: list[str] | None
    :return: Absolute POSIX path string on the remote machine.
    :rtype: str
    """
    mascope_path = get_remote_mascope_path(remote, control_args)
    return str(PurePosixPath(mascope_path) / ".runtime" / "env" / env_name)


def env_exists_local(env_name: str) -> bool:
    """
    Check whether a named environment directory exists locally.

    :param env_name: Name of the runtime environment.
    :type env_name: str
    :return: `True` if the directory exists, `False` otherwise.
    :rtype: bool
    """
    return local_env_dir(env_name).is_dir()


def env_exists_remote(
    remote: str,
    env_name: str,
    control_args: list[str] | None = None,
) -> bool:
    """
    Check whether a named environment directory exists on a remote machine.

    Uses SSH `test -d` to probe the directory — no CLI dependency on the
    remote side.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param env_name: Name of the runtime environment.
    :type env_name: str
    :param control_args: SSH multiplexing flags from `SshMux` to reuse an
                         existing ControlMaster connection. Pass `[]` or
                         `None` for a standalone connection.
    :type control_args: list[str] | None
    :return: `True` if the directory exists on the remote, `False` otherwise.
    :rtype: bool
    """
    path = remote_env_dir(remote, env_name, control_args)
    result = subprocess.run(
        [cygwin_bin("ssh")]
        + get_identity_args()
        + (control_args or [])
        + [remote, "bash", "-l", "-c", f"'test -d {path} && echo exists'"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == "exists"


def get_remote_mascope_path(
    remote: str,
    control_args: list[str] | None = None,
) -> str:
    """
    Resolve `MASCOPE_PATH` on a remote machine by running `mascope path`
    via SSH.

    `MASCOPE_PATH` is set in `/etc/environment` and read directly by the
    `mascope` process — it is NOT exported into the SSH shell environment,
    so `echo $MASCOPE_PATH` returns empty. `mascope path` is the only
    reliable way to retrieve it remotely.

    The command is single-quoted to prevent the local shell (PowerShell
    on Windows) from splitting arguments before SSH passes them to the
    remote bash process.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param control_args: SSH multiplexing flags from `SshMux` to reuse an
                         existing ControlMaster connection. Pass `[]` or
                         `None` for a standalone connection.
    :type control_args: list[str] | None
    :return: Value of `MASCOPE_PATH` on the remote machine.
    :rtype: str
    :raises RuntimeError: If SSH fails or `mascope path` returns empty.
    """
    result = subprocess.run(
        [cygwin_bin("ssh")]
        + get_identity_args()
        + (control_args or [])
        + [remote, "bash", "-l", "-c", "'mascope path'"],
        capture_output=True,
        text=True,
        check=False,
    )
    path = result.stdout.strip()
    runtime.logger.debug(
        f"get_remote_mascope_path({remote}): returncode={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r} path={path!r}"
    )
    if not path:
        raise RuntimeError(
            f"Could not resolve MASCOPE_PATH on {remote} via 'mascope path'. "
            "Ensure Mascope is installed on the remote via tooling/ubuntu.sh."
        )
    return path
