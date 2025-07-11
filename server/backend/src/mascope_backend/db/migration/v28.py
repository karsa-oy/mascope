"""
Migration script to enable WAL mode for improved concurrency.

WAL (Write-Ahead Logging) mode allows multiple readers and a writer
to operate concurrently without blocking each other, eliminating most
"database is locked" errors during concurrent operations.
"""

import os
import shutil

from mascope_backend.db import configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.wal.engine import enable_wal_mode
from mascope_backend.runtime import runtime


async def run():
    """
    Enable WAL mode for the database to improve concurrent access.

    This migration:
    1. Creates a backup of the current database
    2. Copies the database to the new version
    3. Configures the async engine for the new version
    4. Enables WAL mode (setting persists for all future connections)
    """
    # Create backup before migration
    await create_db_backup()

    # Setup database versions
    old_version = 27
    new_version = 28
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    runtime.logger.info(f"Copying database from v{old_version} to v{new_version}")
    shutil.copyfile(old_db_path, new_db_path)

    # Configure async engine for new version
    await configure_database_engine(new_version)

    # Enable WAL mode (this setting will persist across connections)
    success = await enable_wal_mode()

    if success:
        runtime.logger.info("Database now supports improved concurrent access")
        runtime.logger.info(f"Migration to v{new_version} completed successfully")
    else:
        raise RuntimeError("Failed to enable WAL mode during migration")
