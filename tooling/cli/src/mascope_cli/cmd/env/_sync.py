"""
Internal implementation for `mascope env sync`.

Handles filestore sync via rsync and database sync via pg_dump/pg_restore
across local and remote machines. Not a Typer module — contains no commands.

Callers (`env.py`) are responsible for argument parsing and orchestration.

Transfer flow for database sync:
- local → local:  pg_dump source container → transfer/ → pg_restore target container
- remote → local: SSH `mascope {mode} db backup create --transfer` on remote →
                  scp remote transfer/ → local pg_restore from transfer/
- local → remote: local pg_dump → transfer/ → scp → SSH `mascope {mode} db restore --transfer`

Transfer dump lifecycle:
- On success: the specific dump is deleted, then 7-day retention pruning runs.
- On failure: the dump is kept for manual recovery.

Windows note:
- All SSH invocations wrap the remote command in single quotes to prevent
  PowerShell from splitting multi-word arguments before they reach remote bash.
- rsync and scp use Cygwin binaries (C://cygwin64//bin//) on Windows.
"""

import os
import re
import subprocess
from pathlib import Path, PurePosixPath

from mascope_cli.pg import (
    dirs,
    drop_database,
    is_database_ready,
    is_server_ready,
    pg_dump,
    pg_restore,
    purge_old_dumps,
)
from mascope_cli.cmd import lib
from mascope_cli.cmd.env._paths import (
    get_remote_mascope_path,
    parse_address,
)
from mascope_cli.pg.admin import create_database as admin_create_database
from mascope_cli.runtime import runtime


# --- Platform helpers ---


def _cygwin_bin(name: str) -> str:
    """
    Resolve a binary path, using the Cygwin installation on Windows.

    On Linux/macOS returns `name` unchanged. On Windows returns the Cygwin
    path `C://cygwin64//bin//{name}.exe` and raises if not found.

    :param name: Binary name (e.g. `"scp"`, `"rsync"`, `"ssh"`).
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


def _scp(args: list[str]) -> subprocess.CompletedProcess:
    """
    Run an scp command, using Cygwin scp on Windows.

    :param args: scp arguments passed after the binary (source, destination, flags).
    :type args: list[str]
    :return: Completed process result.
    :rtype: subprocess.CompletedProcess
    """
    return subprocess.run([_cygwin_bin("scp")] + args, check=False)


# --- Filestore sync ---


def _to_cygwin_path(path: str) -> str:
    """
    Convert a Windows absolute path to its Cygwin `/cygdrive/` equivalent.

    :param path: Windows path (e.g. `C:\\Users\\foo`).
    :type path: str
    :return: Cygwin-compatible path (e.g. `/cygdrive/c/Users/foo`).
    :rtype: str
    """
    cygwin = re.sub(r"^([A-Z]):\\", lambda m: f"/cygdrive/{m.group(1).lower()}/", path)
    cygwin = cygwin.replace("\\", "/")
    runtime.logger.info(f"Converting path {path} to Cygwin format: {cygwin}")
    return cygwin


def _resolve_rsync_path(remote: str | None, env_name: str) -> str:
    """
    Resolve a sync address to an rsync-compatible path.

    For remote addresses, queries `MASCOPE_PATH` via `mascope path` over SSH
    to construct the full env path without hard-coding it locally.
    See `get_remote_mascope_path` for resolution details.

    :param remote: Remote identifier (`USER@HOST`) or `None` for local.
    :type remote: str | None
    :param env_name: Name of the runtime environment.
    :type env_name: str
    :return: rsync-compatible path string with trailing slash.
    :rtype: str
    """
    if remote is not None:
        mascope_path = get_remote_mascope_path(remote)
        return f"{remote}:{mascope_path}/.runtime/env/{env_name}/"
    return runtime.path(".runtime", "env", f"{env_name}/")


def sync_filestore(source: str, target: str) -> None:
    """
    Sync the filestore from source to target using rsync.

    Resolves both addresses to rsync paths, applies Cygwin path conversion
    on Windows, and runs the rsync command.

    :param source: Source address (`ENV` or `USER@HOST:ENV`).
    :type source: str
    :param target: Target address (`ENV` or `USER@HOST:ENV`).
    :type target: str
    """
    source_remote, source_env = parse_address(source)
    target_remote, target_env = parse_address(target)

    src = _resolve_rsync_path(source_remote, source_env)
    dest = _resolve_rsync_path(target_remote, target_env)

    on_windows = os.name == "nt"
    if on_windows:
        rsync = _cygwin_bin("rsync")
        ssh = _cygwin_bin("ssh")
        src = _to_cygwin_path(src)
        dest = _to_cygwin_path(dest)
    else:
        rsync = "rsync"
        ssh = "ssh"

    flags = " ".join(
        [
            "--progress",
            "--recursive",
            "--copy-links",
            "--keep-dirlinks",
        ]
    )

    cmd = f"{rsync} {flags} -e {ssh} {src} {dest}"
    runtime.logger.info(f"Syncing filestore: {src} → {dest}")
    runtime.logger.info(cmd)
    result = lib.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Filestore sync failed (exit {result.returncode})")


# --- Remote SSH helpers ---


def _ssh_run(remote: str, cmd: str) -> None:
    """
    Execute a command on a remote machine via SSH using a login shell.

    Uses `bash -l -c` so `~/.bashrc` is sourced and `mascope` is available
    on PATH (installed to `~/.local/bin` by `uv tool update-shell`).

    The command string is single-quoted in the SSH invocation to prevent
    the local shell (including PowerShell on Windows) from splitting or
    mangling arguments before they reach the remote bash process.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param cmd: Shell command to execute on the remote.
    :type cmd: str
    :raises RuntimeError: If the SSH command exits non-zero.
    """
    runtime.logger.debug(f"SSH {remote}: bash -l -c '{cmd}'")
    result = subprocess.run(
        ["ssh", remote, "bash", "-l", "-c", f"'{cmd}'"],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"SSH command failed on {remote} (exit {result.returncode}): {cmd}"
        )


def _remote_transfer_dir(remote: str) -> str:
    """
    Return the transfer directory path on a remote machine.

    Delegates to `DatabaseConfig.get_transfer_dir()` with the remote
    `MASCOPE_PATH` so the path structure stays consistent with the local
    config — single source of truth for the transfer directory layout.

    The result is cast through `PurePosixPath` to guarantee forward slashes
    regardless of the local OS — the path is used in SSH/scp commands
    targeting a Linux remote, so Windows backslashes would break it.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :return: Absolute POSIX path string on the remote machine.
    :rtype: str
    """
    mascope_path = get_remote_mascope_path(remote)
    path = runtime.full_config.backend.database.get_transfer_dir(
        mascope_path=mascope_path
    )
    return str(PurePosixPath(path))


# --- Database sync — local operations ---


def _local_transfer_dir() -> Path:
    """
    Resolve the local transfer directory host path from config.

    :return: Absolute host path to `.runtime/database/transfer/`.
    :rtype: Path
    """
    return runtime.full_config.backend.database.get_transfer_dir()


def _dump_local(mode: str, env_name: str) -> Path:
    """
    Create a transfer dump from a local PostgreSQL container.

    Writes the dump to the local transfer directory, which must be
    bind-mounted as `/transfer` in the container. Uses label `"sync"`
    so the filename is identifiable in logs and directory listings.

    :param mode: Mode of the local container to dump from (`"dev"` or `"prod"`).
    :type mode: str
    :param env_name: Environment name whose database to dump.
    :type env_name: str
    :return: Host path to the created `.dump` file.
    :rtype: Path
    :raises RuntimeError: If the server or database is not ready, or if dump fails.
    """
    if not is_server_ready(mode):
        raise RuntimeError(
            f"Local {mode} PostgreSQL is not running — run 'mascope {mode} up' first."
        )
    if not is_database_ready(mode, env_name):
        raise RuntimeError(
            f"Database for env '{env_name}' does not exist in local {mode} PostgreSQL."
        )

    db_cfg = runtime.full_config.backend.database
    container = db_cfg.get_postgres_container_name(mode=mode)
    database = db_cfg.get_postgres_database_name(env_name)
    transfer_dir, transfer_mount = dirs(transfer=True, mode=mode)

    runtime.logger.info(
        f"Dumping '{database}' from local {mode} container → transfer/..."
    )
    return pg_dump(
        container, db_cfg.user, database, transfer_dir, transfer_mount, label="sync"
    )


def _restore_local(mode: str, env_name: str, dump_file: Path) -> None:
    """
    Restore a database in a local PostgreSQL container from a transfer dump.

    Drops and recreates the target database before restoring. The dump file
    must reside in the local transfer directory (bind-mounted as `/transfer`).

    :param mode: Mode of the local container to restore into (`"dev"` or `"prod"`).
    :type mode: str
    :param env_name: Environment name whose database to restore into.
    :type env_name: str
    :param dump_file: Host path to the `.dump` file in the local transfer directory.
    :type dump_file: Path
    :raises RuntimeError: If the server is not ready or any step fails.
    :raises FileNotFoundError: If `dump_file` does not exist on the host.
    """
    if not is_server_ready(mode):
        raise RuntimeError(
            f"Local {mode} PostgreSQL is not running — run 'mascope {mode} up' first."
        )

    db_cfg = runtime.full_config.backend.database
    container = db_cfg.get_postgres_container_name(mode=mode)
    database = db_cfg.get_postgres_database_name(env_name)
    _, transfer_mount = dirs(transfer=True, mode=mode)

    runtime.logger.info(f"Dropping '{database}' in local {mode} container...")
    drop_database(container, db_cfg.user, database)

    runtime.logger.info(f"Creating empty '{database}'...")
    admin_create_database(container, db_cfg.user, database)

    runtime.logger.info(f"Restoring '{database}' from '{dump_file.name}'...")
    pg_restore(container, db_cfg.user, database, dump_file, transfer_mount)


# --- Database sync — remote operations ---


def _dump_remote(remote: str, mode: str, env_name: str) -> None:
    """
    Trigger a transfer dump on a remote machine via SSH.

    Calls `mascope {mode} db backup create --env ENV --transfer --yes` on
    the remote, writing the dump into the remote transfer directory.
    The `--label sync` flag is passed so the file is identifiable in logs.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param mode: Mode on the remote machine (`"dev"` or `"prod"`).
    :type mode: str
    :param env_name: Environment name to dump on the remote.
    :type env_name: str
    :raises RuntimeError: If the SSH command fails.
    """
    cmd = f"mascope {mode} db backup create --env {env_name} --transfer --label sync --yes"
    runtime.logger.info(f"Triggering remote dump on {remote}: {cmd}")
    _ssh_run(remote, cmd)


def _restore_remote(remote: str, mode: str, env_name: str) -> None:
    """
    Trigger a transfer restore on a remote machine via SSH.

    Calls `mascope {mode} db restore --env ENV --transfer --yes` on the
    remote, restoring from the latest dump in the remote transfer directory.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param mode: Mode on the remote machine (`"dev"` or `"prod"`).
    :type mode: str
    :param env_name: Environment name to restore into on the remote.
    :type env_name: str
    :raises RuntimeError: If the SSH command fails.
    """
    cmd = f"mascope {mode} db restore --env {env_name} --transfer --yes"
    runtime.logger.info(f"Triggering remote restore on {remote}: {cmd}")
    _ssh_run(remote, cmd)


def _scp_pull(remote: str, db_name: str) -> Path:
    """
    Pull the latest transfer dump for `db_name` from a remote machine.

    Lists the remote transfer directory via SSH, finds the newest matching
    file, and copies it to the local transfer directory via scp.

    The `ls` command is single-quoted to prevent PowerShell on Windows from
    splitting the glob pattern before SSH passes it to the remote bash process.
    On Windows, the local destination path is converted to a Cygwin
    `/cygdrive/` path — Cygwin scp interprets `C:\...` as `HOST:PATH`.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param db_name: Database name prefix used to filter files
                    (e.g. `mascope_tof1`).
    :type db_name: str
    :return: Local host path to the downloaded `.dump` file.
    :rtype: Path
    :raises RuntimeError: If no matching file is found on the remote or scp fails.
    """
    remote_dir = _remote_transfer_dir(remote)
    ls_cmd = f"ls -t {remote_dir}/{db_name}_*.dump 2>/dev/null | head -1"

    result = subprocess.run(
        ["ssh", remote, "bash", "-l", "-c", f"'{ls_cmd}'"],
        capture_output=True,
        text=True,
        check=False,
    )
    runtime.logger.debug(
        f"_scp_pull ls on {remote}: returncode={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    remote_file = result.stdout.strip()
    if not remote_file:
        raise RuntimeError(
            f"No transfer dump found for '{db_name}' in {remote}:{remote_dir}/"
        )

    filename = Path(remote_file).name
    local_dir = _local_transfer_dir()
    local_dir.mkdir(parents=True, exist_ok=True)
    local_file = local_dir / filename

    # Cygwin scp interprets Windows paths (C:\...) as HOST:PATH — must use
    # Cygwin /cygdrive/ paths for local arguments on Windows.
    local_file_arg = (
        _to_cygwin_path(str(local_file)) if os.name == "nt" else str(local_file)
    )

    runtime.logger.info(f"Pulling {remote}:{remote_file} → {local_file}")
    result = _scp([f"{remote}:{remote_file}", local_file_arg])
    if result.returncode != 0:
        raise RuntimeError(f"scp failed pulling '{remote_file}' from {remote}")
    return local_file


def _scp_push(remote: str, dump_file: Path) -> None:
    """
    Push a local transfer dump to the remote machine's transfer directory.

    Creates the remote transfer directory if it does not exist, then copies
    the file via scp. On Windows, the local source path is converted to a
    Cygwin `/cygdrive/` path — Cygwin scp interprets `C:\...` as `HOST:PATH`.

    :param remote: Remote identifier in `USER@HOST` format.
    :type remote: str
    :param dump_file: Local host path to the `.dump` file to push.
    :type dump_file: Path
    :raises RuntimeError: If scp fails.
    """
    remote_dir = _remote_transfer_dir(remote)
    _ssh_run(remote, f"mkdir -p {remote_dir}")

    # Cygwin scp interprets Windows paths (C:\...) as HOST:PATH — must use
    # Cygwin /cygdrive/ paths for local arguments on Windows.
    dump_file_arg = (
        _to_cygwin_path(str(dump_file)) if os.name == "nt" else str(dump_file)
    )

    runtime.logger.info(f"Pushing {dump_file.name} → {remote}:{remote_dir}/")
    result = _scp([dump_file_arg, f"{remote}:{remote_dir}/{dump_file.name}"])
    if result.returncode != 0:
        raise RuntimeError(f"scp failed pushing '{dump_file.name}' to {remote}")


# --- Transfer cleanup ---


def _cleanup_transfer(dump_file: Path, db_name: str, retention_days: int = 7) -> None:
    """
    Delete a specific transfer dump and prune older ones beyond the retention window.

    Called on successful restore. On failure, callers skip this so the dump
    is preserved for manual recovery.

    Only files whose name starts with `db_name` are considered for pruning —
    other databases' dumps in the shared transfer directory are not touched.

    :param dump_file: The specific dump file to delete immediately.
    :type dump_file: Path
    :param db_name: Database name prefix used to filter files for pruning
                    (e.g. `mascope_tof1`).
    :type db_name: str
    :param retention_days: Also delete any other dumps for `db_name` older
                           than this many days. Default: 7.
    :type retention_days: int
    """
    if dump_file.exists():
        dump_file.unlink()
        runtime.logger.info(f"Deleted transfer dump: {dump_file.name}")

    transfer_dir = _local_transfer_dir()
    deleted = purge_old_dumps(transfer_dir, db_name, retention_days)
    for f in deleted:
        runtime.logger.info(f"Pruned old transfer dump: {f.name}")


# --- Database sync — orchestration ---


def sync_db(
    source: str,
    source_mode: str,
    target: str,
    target_mode: str,
) -> None:
    """
    Sync a PostgreSQL database from source to target.

    Handles three topology cases:

    - local → local:  dump from source container → transfer/ → restore to target container
    - remote → local: SSH dump on remote → scp to local transfer/ → restore to local container
    - local → remote: dump from local container → transfer/ → scp to remote → SSH restore

    Remote → remote is not supported — run the command from one of the machines.

    On successful restore, the transfer dump is deleted and 7-day retention
    pruning runs for the same database. On failure, the dump is preserved for
    manual recovery.

    :param source: Source address (`ENV` or `USER@HOST:ENV`).
    :type source: str
    :param source_mode: Mode on the source machine (`"dev"` or `"prod"`).
    :type source_mode: str
    :param target: Target address (`ENV` or `USER@HOST:ENV`).
    :type target: str
    :param target_mode: Mode on the target machine (`"dev"` or `"prod"`).
    :type target_mode: str
    :raises ValueError: If both source and target are remote (unsupported topology).
    :raises RuntimeError: If any step of the sync fails.
    """
    source_remote, source_env = parse_address(source)
    target_remote, target_env = parse_address(target)

    if source_remote is not None and target_remote is not None:
        raise ValueError(
            "Remote → remote sync is not supported. "
            "Run the sync from one of the machines directly."
        )

    db_cfg = runtime.full_config.backend.database
    source_db = db_cfg.get_postgres_database_name(source_env)

    runtime.logger.info(
        f"Syncing database: {source} ({source_mode}) → {target} ({target_mode})"
    )

    if source_remote is None and target_remote is None:
        # local → local
        dump_file = _dump_local(source_mode, source_env)
        _restore_local(target_mode, target_env, dump_file)
        _cleanup_transfer(dump_file, source_db)

    elif source_remote is not None:
        # remote → local
        _dump_remote(source_remote, source_mode, source_env)
        dump_file = _scp_pull(source_remote, source_db)
        remote_file = f"{_remote_transfer_dir(source_remote)}/{dump_file.name}"
        _restore_local(target_mode, target_env, dump_file)
        # Clean local transfer dump and prune old local dumps
        _cleanup_transfer(dump_file, source_db)
        # Remove the staged dump from the remote transfer dir
        _ssh_run(source_remote, f"rm -f {remote_file}")

    else:
        # local → remote
        dump_file = _dump_local(source_mode, source_env)
        _scp_push(target_remote, dump_file)
        _restore_remote(target_remote, target_mode, target_env)
        # Clean local transfer dump
        _cleanup_transfer(dump_file, source_db)
        # Remove the staged dump from the remote transfer dir
        remote_file = f"{_remote_transfer_dir(target_remote)}/{dump_file.name}"
        _ssh_run(target_remote, f"rm -f {remote_file}")
