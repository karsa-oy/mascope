import asyncio
import os
import sqlite3

from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.runtime import runtime


# -----------------------------
# Async entry point for maintenance
# -----------------------------


async def db_maintenance():
    """
    Asynchronously performs maintenance operations on the database.
    This includes creating a backup, vacuuming to defragment the database, analyzing for query optimization,
    and checking database integrity.
    """
    await create_db_backup()

    # Determine the current version and paths
    data_path = runtime.config.database
    current_version = get_current_db_version()
    db_path = os.path.join(data_path, f"mascope.v{current_version}.db")

    # Perform the maintenance tasks asynchronously
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, perform_maintenance, db_path)


# -----------------------------
# Sync wrapper for CLI or synchronous environments
# -----------------------------


def run_db_maintenance():
    """
    Synchronously performs database maintenance by wrapping the async method.
    This is useful for CLI environments where sync is preferred.
    """
    asyncio.run(db_maintenance())


# -----------------------------
# Helper functions for maintenance operation
# -----------------------------


def perform_maintenance(db_path):
    """
    Performs the maintenance operations such as VACUUM, ANALYZE, and checking the database integrity.
    """
    conn = sqlite3.connect(db_path)
    with conn:
        # Perform a VACUUM operation to rebuild the database and optimize disk space
        runtime.logger.info("Performing VACUUM...")
        conn.execute("VACUUM")

        # Perform an ANALYZE operation to optimize the database's internal statistics for better query planning
        runtime.logger.info("Performing ANALYZE...")
        conn.execute("ANALYZE")

        # Log indexes after ANALYZE
        runtime.logger.info("Indexes after maintenance:")
        log_indexes(conn)

        # Other maintenance operations could be added here
        runtime.logger.info("Checking database integrity...")
        result = conn.execute("PRAGMA integrity_check")
        integrity_result = result.fetchone()
        runtime.logger.info(f"Integrity check result: {integrity_result}")
    runtime.logger.info("Database maintenance operations completed successfully.")


def log_indexes(conn):
    """Logs the indexes of all tables in the database and counts manual and auto-created indexes."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    manual_index_count = 0
    auto_index_count = 0

    for table in tables:
        runtime.logger.debug(f"Indexes for table {table[0]}:")
        cursor.execute(f"PRAGMA index_list({table[0]})")
        indexes = cursor.fetchall()
        for index in indexes:
            runtime.logger.info(index)
            if "idx_" in index[1] or "ix_" in index[1]:
                manual_index_count += 1
            elif "sqlite_autoindex_" in index[1]:
                auto_index_count += 1

    runtime.logger.info("Summary of Index Usage:")
    runtime.logger.info(f"Manual indexes count: {manual_index_count}")
    runtime.logger.info(f"Auto-created indexes count: {auto_index_count}")
    if manual_index_count == 0 and auto_index_count == 0:
        runtime.logger.warning("No indexes found, please verify if this is expected.")
