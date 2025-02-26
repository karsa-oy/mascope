"""
Migration script for v19 to v20 database migration.
"""

import os
import shutil
import asyncio

from mascope_server.db import configure_database_engine
from mascope_server.db.ops.restore import db_restore
from mascope_server.db.ops.maintenance import db_maintenance
from mascope_server.db.ops.clean_access_tokens import clean_access_tokens
from mascope_server.db.ops.backup import create_db_backup
from mascope_server.runtime import runtime


async def run():
    """
    Execute the v19 to v20 database migration:
    1. Restoring tables with schema inconsistencies (target_isotope)
    2. Removing orphaned sample_item records with no corresponding sample_file
    3. Cleaning up invalid access tokens after renaming mascope_api to mascope_sdk
    4. Running database maintenance operations
    """
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    new_version = 20
    old_db_path = os.path.join(runtime.config.database, "mascope.v19.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    await configure_database_engine(new_version)

    # Step 1: Run db_restore
    # - to fix target_isotope schema inconsistencies
    # - remove orphaned sample_items records
    await db_restore()

    # Step 2: Clean up invalid access tokens (after renaming mascope_api to mascope_sdk)
    await clean_access_tokens()

    # Step 3: Run database maintenance operations
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully.")


if __name__ == "__main__":
    asyncio.run(run())
