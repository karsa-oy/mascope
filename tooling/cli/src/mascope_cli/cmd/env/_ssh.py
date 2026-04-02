"""
Shared SSH helpers for `mascope env` commands.

Provides platform-aware binary resolution, identity file args, and SSH
multiplexing. Used by `_paths.py`, `_create.py`, and `_sync.py`.

SSH multiplexing:
- `SshMux` opens a ControlMaster connection for the duration of the sync so
  all SSH/scp calls share one authenticated session — password prompted once.
- `SshMux.__enter__` returns `list[str]` (the control args), so both
  `SshMux(remote)` and `nullcontext(existing_args)` yield the same type —
  no isinstance checks needed at call sites.
- On Windows/Cygwin, ControlMaster is not supported — `SshMux.__enter__`
  returns `[]` immediately. Key-based auth via `get_identity_args()` handles
  authentication without multiplexing.
"""

import os
import subprocess
import tempfile

from mascope_cli.runtime import runtime


def cygwin_bin(name: str) -> str:
    """
    Resolve a binary path, using the Cygwin installation on Windows.

    On Linux/macOS returns `name` unchanged. On Windows returns the Cygwin
    path `C://cygwin64//bin//{name}.exe` and raises if not found.

    :param name: Binary name (e.g. `"ssh"`, `"scp"`, `"rsync"`).
    :type name: str
    :return: Resolved binary path.
    :rtype: str
    :raises RuntimeError: On Windows if the Cygwin binary is not found.
    """
    if os.name != "nt":
        return name
    path = rf"C://cygwin64//bin//{name}.exe"
    if not os.path.exists(path):
        raise RuntimeError(
            f"Cygwin {name} not found at {path}. Please install Cygwin with {name}."
        )
    return path


def get_identity_args() -> list[str]:
    """
    Return SSH identity file args for mascope sync operations.

    Resolution order:

    1. Cygwin `~/.ssh/mascope_sync` — dedicated no-passphrase sync key
    2. Windows `~/.ssh/mascope_sync` — same key copied to Windows OpenSSH location
    3. Empty list — fall back to default key resolution / password prompt

    On Windows, Cygwin home is resolved via Cygwin bash — `USERNAME` env
    var may differ from the Cygwin username. Existence check also goes through
    Cygwin bash (`test -f`) since Python's `os.path.exists` resolves
    against the Windows filesystem and cannot see Cygwin's virtual `/home/`.

    On Linux, returns `["-i", "~/.ssh/mascope_sync"]` if the key exists,
    `[]` otherwise — falls back to the default key (`id_ed25519`, etc.)
    and standard passphrase prompting.

    :return: `["-i", "<path>"]` or `[]`.
    :rtype: list[str]
    """
    if os.name != "nt":
        key_path = os.path.expanduser("~/.ssh/mascope_sync")
        return ["-i", key_path] if os.path.exists(key_path) else []

    # 1. Cygwin ~/.ssh/mascope_sync
    cygwin_result = subprocess.run(
        [cygwin_bin("bash"), "-l", "-c", "echo ~/.ssh/mascope_sync"],
        capture_output=True,
        text=True,
        check=False,
    )
    cygwin_key = cygwin_result.stdout.strip()
    if cygwin_key:
        exists_result = subprocess.run(
            [cygwin_bin("bash"), "-l", "-c", f"test -f {cygwin_key} && echo yes"],
            capture_output=True,
            text=True,
            check=False,
        )
        if exists_result.stdout.strip() == "yes":
            return ["-i", cygwin_key]

    # 2. Windows ~/.ssh/mascope_sync
    windows_key = os.path.expanduser("~/.ssh/mascope_sync")
    if os.path.exists(windows_key):
        return ["-i", windows_key]

    # 3. Fallback — default key resolution
    return []


class SshMux:
    """
    Context manager that opens an SSH ControlMaster connection for a remote
    host and tears it down on exit, so all SSH/scp calls within the context
    reuse a single authenticated session — password prompted at most once.

    `__enter__` returns `list[str]` (the ControlMaster `-o` flags),
    so `SshMux` and `nullcontext(existing_args)` yield the same type
    and can be used interchangeably without isinstance checks::

        ctx = nullcontext(control_args) if control_args is not None else SshMux(remote)
        with ctx as ctl:
            _ssh_run(remote, cmd, ctl)

    On Windows/Cygwin, ControlMaster is not supported — `__enter__` returns
    `[]` immediately and `__exit__` is a no-op. Key-based auth via
    `get_identity_args()` handles authentication without multiplexing.

    On Linux, falls back gracefully if ControlMaster setup fails — `__enter__`
    returns `[]` and all subsequent calls behave as individual connections.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    """

    def __init__(self, remote: str) -> None:
        self._remote = remote
        self._socket: str | None = None

    def __enter__(self) -> list[str]:
        """
        Open the ControlMaster connection and return the SSH control flags.

        On Windows/Cygwin, ControlMaster is not supported — returns `[]`
        immediately without attempting a connection.

        :return: `["-o", "ControlMaster=auto", "-o", "ControlPath=<socket>"]`
                 on success, `[]` if ControlMaster is not active or not
                 supported (Windows/Cygwin).
        :rtype: list[str]
        """
        if os.name == "nt":
            runtime.logger.info(
                "SshMux: ControlMaster not supported on Windows/Cygwin — "
                "using key-based auth without multiplexing"
            )
            return []

        socket_dir = tempfile.gettempdir()
        safe_remote = self._remote.replace("@", "_").replace(".", "_")
        self._socket = f"{socket_dir}/mascope_mux_{safe_remote}"

        # Remove stale socket — prevents "already exists, disabling multiplexing"
        # when a previous run crashed without cleanup.
        if os.path.exists(self._socket):
            try:
                os.remove(self._socket)
            except OSError:
                pass

        runtime.logger.info(
            f"SshMux: opening ControlMaster to {self._remote} (socket: {self._socket})"
        )
        result = subprocess.run(
            [
                "ssh",
                "-M",
                "-N",
                "-f",
                *get_identity_args(),
                "-o",
                "ControlMaster=yes",
                "-o",
                f"ControlPath={self._socket}",
                "-o",
                "ControlPersist=600",
                "-o",
                "ServerAliveInterval=30",
                "-o",
                "ServerAliveCountMax=6",
                self._remote,
            ],
            check=False,
        )
        if result.returncode != 0:
            runtime.logger.warning(
                f"SshMux: failed to open ControlMaster to {self._remote} "
                f"(exit {result.returncode}) — falling back to individual connections"
            )
            self._socket = None

        return self._control_args()

    def __exit__(self, *_) -> None:
        # Linux only — Windows returns [] from __enter__ without setting _socket.
        if not self._socket:
            return
        runtime.logger.info(f"SshMux: closing ControlMaster to {self._remote}")
        subprocess.run(
            [
                "ssh",
                "-O",
                "exit",
                "-o",
                f"ControlPath={self._socket}",
                self._remote,
            ],
            check=False,
            capture_output=True,  # suppress "Exit request sent." noise
        )
        self._socket = None

    def _control_args(self) -> list[str]:
        """
        Return the SSH `-o` flags for multiplexing.

        :return: `["-o", "ControlMaster=auto", "-o", "ControlPath=<socket>"]`
                 or `[]` if the ControlMaster is not active.
        :rtype: list[str]
        """
        if not self._socket:
            return []
        return [
            "-o",
            "ControlMaster=auto",
            "-o",
            f"ControlPath={self._socket}",
        ]
