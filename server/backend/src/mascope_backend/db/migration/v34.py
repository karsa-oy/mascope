"""
Migration script for v34: Add status column to sample_batch table.

Schema changes:
- Add status VARCHAR(20) field to sample_batch table with default 'ready'
- All existing batches will have status='ready' after migration
"""

import asyncio
import os
import shutil

from sqlalchemy import text

from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


async def run():
    """
    Add status column to sample_batch table.
    """
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 33
    new_version = 34
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    # Configure async engine for new version
    await configure_database_engine(new_version)

    # Step 3: Apply schema migration
    runtime.logger.info("Adding status column to sample_batch table")
    await add_status_column_to_sample_batch()

    # Step 4: Run database maintenance
    await db_restore()
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully")


async def add_status_column_to_sample_batch():
    """
    Add status column to sample_batch table with default value 'ready'.
    """
    async with async_session() as session:
        default_status = sample_batch_config.DEFAULT_SAMPLE_BATCH_STATUS
        await session.execute(
            text(
                f"ALTER TABLE sample_batch ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT '{default_status}'"
            )
        )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
