"""
Migration script for v20 to v21 database migration.
"""

import asyncio
import os
import shutil

from sqlalchemy import select

from mascope_backend.api.controllers.match.match_controller import (
    rematch_batches,
)
from mascope_backend.api.models.match.match_pydantic_model import (
    RematchBatchBody,
    RematchBatchesBody,
)
from mascope_backend.db import SampleBatch, async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.filestore import delete_sum_signal, refit_peaks
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


async def run():
    """
    Execute the v20 to v21 database migration:
    1. Prepare new database
    2. Delete "peak_heights", "peak_areas" and "sum_signal" from all files in the filestore
    3. Compute all peaks to all files in the filestore
    4. Restore tables with schema inconsistencies
    5. Rematch all batches
    6. Run database maintenance operations
    """
    # Step 1: Prepare new database

    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    new_version = 21
    old_db_path = os.path.join(runtime.config.database, "mascope.v20.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    await configure_database_engine(new_version)

    # Step 2: Delete deprecated data from the filestore
    runtime.logger.info("Deleting deprecated data from the filestore.")
    await delete_sum_signal()

    # Step 3: Compute all peaks to all files in the filestore
    runtime.logger.info("Computing all peaks to all files in the filestore.")
    await refit_peaks()

    # Step 4: Run db_restore
    await db_restore()

    # Step 5: Rematch all batches

    # Get all sample batches
    async with async_session() as session:
        stmt = select(SampleBatch)
        result = await session.execute(stmt)
        sample_batch_list = result.scalars().all()

    runtime.logger.info(f"Rematching {len(sample_batch_list)} sample batches.")

    sample_batch_ids = [
        sample_batch.sample_batch_id for sample_batch in sample_batch_list
    ]
    rematch_batch_bodies = [
        RematchBatchBody(sample_batch_id=sample_batch_id)
        for sample_batch_id in sample_batch_ids
    ]
    rematch_batches_body = RematchBatchesBody(sample_batches=rematch_batch_bodies)

    await rematch_batches(
        rematch_batches_body, independent_transaction=True, sid="", process_id=""
    )

    # Step 6: Run database maintenance operations
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully.")


if __name__ == "__main__":
    asyncio.run(run())
