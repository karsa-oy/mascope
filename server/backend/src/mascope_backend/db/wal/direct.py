"""
Direct SQLite WAL operations module.

Provides direct sqlite3 connection-based WAL operations for CLI commands
and scenarios where async engine is not available.
"""

import os
import sqlite3
from sqlite3 import Error as SQLiteError
from typing import Literal

from mascope_backend.db.utils import get_current_db_path
from mascope_backend.runtime import runtime


def get_journal_mode() -> str | None:
    """
    Get current journal mode using direct SQLite connection.

    :return: Current journal mode (e.g., 'wal', 'delete') or None if error
    :rtype: str | None
    """
    try:
        db_path = get_current_db_path()
        with sqlite3.connect(db_path) as conn:
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            runtime.logger.info(f"Current journal mode: {journal_mode}")
            return journal_mode.lower()
    except Exception as e:
        runtime.logger.error(f"Error getting journal mode: {e}")
        return None


def set_journal_mode(mode: str = "wal") -> str | None:
    """
    Set SQLite journal mode using direct connection.

    :param mode: Journal mode to set ('wal' or 'delete')
    :return: New journal mode or None if error
    :rtype: str | None
    """
    mode = mode.lower()
    if mode not in {"wal", "delete"}:
        raise ValueError(f"Unsupported journal mode: {mode}")

    try:
        db_path = get_current_db_path()
        with sqlite3.connect(db_path) as conn:
            result = conn.execute(f"PRAGMA journal_mode={mode}").fetchone()
            new_mode = result[0] if result else None
            runtime.logger.info(f"Journal mode set to: {new_mode}")
            return new_mode
    except Exception as e:
        runtime.logger.error(f"Error setting journal mode: {e}")
        return None


def direct_wal_checkpoint(
    mode: Literal["PASSIVE", "FULL", "RESTART", "TRUNCATE"] = "RESTART",
) -> bool:
    """
    Perform WAL checkpoint using direct SQLite connection.

    Modes and their behavior:
    - PASSIVE (default): Non-blocking checkpoint that doesn't interfere with other connections.
      Use after heavy write operations during normal app operation.
      Returns immediately if database is busy.

    - FULL: Blocks new writers but allows readers. Tries to complete checkpoint.
      Use during maintenance windows or before backups.
      May briefly block if database is active.

    - RESTART: Blocks new writers and waits for all readers to finish.
      Ensures next writer will restart WAL from beginning.
      Use for critical operations requiring a clean WAL state.

    - TRUNCATE: Most aggressive mode. Completes checkpoint and truncates WAL to 0 bytes.
      Use during application shutdown, migrations, or when exclusive access is guaranteed.


    :param mode: Checkpoint mode (PASSIVE, FULL, RESTART, TRUNCATE)
    :return: True if checkpoint completed successfully
    :rtype: bool
    """
    valid_modes = {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}
    if mode not in valid_modes:
        raise ValueError(
            f"Invalid checkpoint mode: {mode}. Use PASSIVE/FULL/RESTART/TRUNCATE"
        )

    try:
        db_path = get_current_db_path()
        wal_path = f"{db_path}-wal"

        # Get WAL size before checkpoint
        size_before = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0

        with sqlite3.connect(db_path) as conn:
            # Verify WAL mode
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            if journal_mode.lower() != "wal":
                runtime.logger.debug(
                    f"Checkpoint skipped - not in WAL mode ({journal_mode})"
                )
                return False

            # Execute checkpoint
            result = conn.execute(f"PRAGMA wal_checkpoint({mode})").fetchone()
            if not result:
                return False

            busy, log_pages, checkpointed = result

            # Get WAL size after checkpoint
            size_after = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0

            runtime.logger.debug(
                f"{mode} checkpoint: busy={busy}, "
                f"log_pages={log_pages}, "
                f"checkpointed={checkpointed}, "
                f"wal_size={size_before}=>{size_after} bytes"
            )

            # Determine success based on checkpoint mode
            if mode == "TRUNCATE":
                # TRUNCATE mode success: WAL file should be 0 bytes and not blocked
                success = (busy == 0) and (size_after == 0)
                if not success and busy == 0:
                    runtime.logger.warning(
                        f"TRUNCATE checkpoint completed but WAL not truncated (size: {size_after} bytes)"
                    )
            else:
                # Other modes success: checkpoint not blocked (WAL may still have content)
                success = busy == 0
                if success and log_pages > 0:
                    runtime.logger.debug(
                        f"{mode} checkpoint completed with {log_pages} pages remaining in WAL"
                    )

            return success
    except SQLiteError as e:
        if e.sqlite_errorcode == sqlite3.SQLITE_BUSY:
            runtime.logger.warning("Checkpoint aborted - database busy (SQLITE_BUSY)")
        elif e.sqlite_errorcode == sqlite3.SQLITE_LOCKED:
            runtime.logger.warning(
                "Checkpoint aborted - database locked (SQLITE_LOCKED)"
            )
        else:
            runtime.logger.error(
                f"Checkpoint error [{e.sqlite_errorcode}]: {e.sqlite_errorname} - {e}"
            )
        return False
    except FileNotFoundError:
        runtime.logger.debug("WAL file not found - skipping size check")
        return True
    except Exception as e:
        runtime.logger.error(f"Unexpected checkpoint error: {e}")
        return False


def check_wal_status():
    """
    Check and log current WAL configuration and statistics using direct connection.

    Provides comprehensive WAL status logging including file information, checkpoint status,
    and database configuration. Uses direct SQLite connection for CLI and app use.

    NOTE: PRAGMA wal_checkpoint is designed to do a passive checkpoint and return the status.
    So if we want to know the current state of the WAL, we have to run a passive checkpoint.
    """
    try:
        db_path = get_current_db_path()
        wal_path = f"{db_path}-wal"
        shm_path = f"{db_path}-shm"

        with sqlite3.connect(db_path) as conn:
            # Get basic database info
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

            # Check file existence and sizes
            wal_file_exists = os.path.exists(wal_path)
            shm_file_exists = os.path.exists(shm_path)
            wal_size = os.path.getsize(wal_path) if wal_file_exists else 0
            shm_size = os.path.getsize(shm_path) if shm_file_exists else 0

            # Log basic WAL status
            runtime.logger.info("Database WAL Status:")
            runtime.logger.info(f"  Journal Mode: {journal_mode}")
            runtime.logger.info(f"  Busy Timeout: {busy_timeout}ms")
            runtime.logger.info(f"  WAL file exists: {wal_file_exists}")
            if wal_file_exists:
                runtime.logger.info(
                    f"  WAL size: {wal_size} bytes ({wal_size/1024:.1f}KB)"
                )
            runtime.logger.info(f"  SHM file exists: {shm_file_exists}")
            if shm_file_exists:
                runtime.logger.info(
                    f"  SHM size: {shm_size} bytes ({shm_size/1024:.1f}KB)"
                )

            # If WAL mode is active, get checkpoint statistics
            if journal_mode.lower() == "wal":
                try:
                    # Get WAL checkpoint info (does passive checkpoint)
                    checkpoint_result = conn.execute("PRAGMA wal_checkpoint").fetchone()
                    if checkpoint_result:
                        busy, log_pages, checkpointed = checkpoint_result
                        runtime.logger.info(
                            f"  WAL checkpoint: busy={busy}, log_pages={log_pages}, checkpointed={checkpointed}"
                        )
                    else:
                        runtime.logger.debug("  WAL checkpoint: no result returned")
                except Exception as e:
                    runtime.logger.warning(f"Could not get WAL checkpoint status: {e}")
            else:
                runtime.logger.debug("Checkpoint info skipped - not in WAL mode")

    except Exception as e:
        runtime.logger.error(f"Error checking WAL status: {e}")
