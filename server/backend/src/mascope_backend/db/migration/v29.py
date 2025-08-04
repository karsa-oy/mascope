"""
Migration script for v28 to v29 database migration.
"""

import os
import shutil

from mascope_backend.db import (
    configure_database_engine,
)
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.backup import create_db_backup

from mascope_backend.runtime import runtime


async def run():
    """
    Execute the v28 to v29 database migration
    """
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    new_version = 29
    old_db_path = os.path.join(runtime.config.database, "mascope.v28.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)

    # Clean up the database
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully.")
    runtime.logger.info(
        "Note: Rematching will be performed in v30 migration after schema updates."
    )
