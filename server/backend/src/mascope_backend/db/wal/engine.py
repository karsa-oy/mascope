"""
Async SQLAlchemy WAL operations module.

Provides async WAL operations that work within the application's
SQLAlchemy async session context. Safe for concurrent operations.
"""

from sqlalchemy import text

from mascope_backend.db import async_session
from mascope_backend.runtime import runtime


async def enable_wal_mode() -> bool:
    """
    Enable WAL mode for the current database using async session.

    Unlike the other journaling modes, PRAGMA journal_mode=WAL is persistent.
    If a process sets WAL mode, then closes and reopens the database, the database
    will come back in WAL mode.

    :return: True if WAL mode was enabled successfully
    :rtype: bool
    """
    try:
        async with async_session() as session:
            # Check current mode
            current_mode = await session.execute(text("PRAGMA journal_mode"))
            mode_result = current_mode.scalar()

            if mode_result == "wal":
                runtime.logger.info("WAL mode already enabled")
                return True

            # Enable WAL mode
            wal_result = await session.execute(text("PRAGMA journal_mode=WAL"))
            new_mode = wal_result.scalar()

            if new_mode == "wal":
                runtime.logger.info("WAL mode enabled successfully")
                return True
            else:
                runtime.logger.error(f"Failed to enable WAL mode: {new_mode}")
                return False

    except Exception as e:
        runtime.logger.error(f"Error enabling WAL mode: {e}")
        return False


async def wal_checkpoint():
    """
    Perform non-blocking PASSIVE WAL checkpoint using current app async session.

    PASSIVE mode is safe for concurrent operations as it doesn't block
    other connections and returns immediately if database is busy.

    For blocking checkpoint modes, use direct_wal_checkpoint() from direct module.
    """
    try:
        async with async_session() as session:
            # Check journal mode
            journal_mode = await session.execute(text("PRAGMA journal_mode"))
            if journal_mode.scalar().lower() != "wal":
                runtime.logger.debug("Checkpoint skipped - not in WAL mode")

            # Execute passive checkpoint
            result = await session.execute(text("PRAGMA wal_checkpoint(PASSIVE)"))
            checkpoint_info = result.fetchone()

            if not checkpoint_info:
                runtime.logger.debug("PASSIVE checkpoint: no result returned")

            busy, log_pages, checkpointed = checkpoint_info

            # Log results
            runtime.logger.debug(
                f"PASSIVE checkpoint: busy={busy}, "
                f"log_pages={log_pages}, "
                f"checkpointed={checkpointed}"
            )

    except Exception as e:
        runtime.logger.error(f"Error during PASSIVE checkpoint: {e}")
