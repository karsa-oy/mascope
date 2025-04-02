"""
Migration script for v21 to v22 database migration.
"""

import os
import shutil
import asyncio

from sqlalchemy import text, select
from mascope_backend.db import (
    async_session,
    configure_database_engine,
)
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.models import SampleItem
from mascope_backend.runtime import runtime
from mascope_signal.compute import get_scan_timestamps


async def run():
    """
    Execute the v21 to v22 database migration
    """
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    new_version = 22
    old_db_path = os.path.join(runtime.config.database, "mascope.v21.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)

    # Modify the database schema for the v22 migration
    await modify_schema()

    # Clean up the database
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully.")


async def modify_schema():
    """
    Modify the database schema for the v22 migration.
    """
    runtime.logger.info("Executing schema migration...")
    async with async_session() as session:

        runtime.logger.info("Add polarity, tic, t0, t1 columns to sample_item...")
        await session.execute(
            text("ALTER TABLE sample_item ADD COLUMN polarity VARCHAR(1);")
        )
        await session.execute(text("ALTER TABLE sample_item ADD COLUMN tic FLOAT;"))
        await session.execute(text("ALTER TABLE sample_item ADD COLUMN t0 FLOAT;"))
        await session.execute(text("ALTER TABLE sample_item ADD COLUMN t1 FLOAT;"))

        runtime.logger.info(
            "Update sample_item tic and polarity columns with data from sample_view..."
        )
        await session.execute(
            text(
                """
            UPDATE sample_item
            SET 
                polarity = sample_view.polarity,
                tic = sample_view.tic
            FROM sample_view
            WHERE sample_item.sample_item_id = sample_view.sample_item_id;
        """
            )
        )

        runtime.logger.info("Populating t0 and t1 columns in sample_item...")
        await populate_time_range(session)

        runtime.logger.info("Updating sample_view with sample_item new columns...")
        await update_sample_view(session)

        runtime.logger.info("Drop columns from sample_file...")
        await session.execute(text("ALTER TABLE sample_file DROP COLUMN tic;"))

        await session.commit()
        runtime.logger.info("Schema migration completed successfully!")


async def populate_time_range(session):
    """Fill in t0...t1 columns in sample_item."""
    stmt = select(SampleItem)
    result = await session.execute(stmt)
    sample_items = result.scalars().all()

    for sample_item in sample_items:
        filename = sample_item.filename
        scan_timestamps = get_scan_timestamps(filename)

        # Set t0 and t1 based on the scan timestamps
        sample_item.t0 = scan_timestamps[0]
        sample_item.t1 = scan_timestamps[-1]


async def update_sample_view(session):
    """
    Updates the sample_view after adding columns to sample_item.
    """
    await session.execute(text("DROP VIEW IF EXISTS sample_view"))

    # Recreate the view
    await session.execute(
        text(
            """
            CREATE VIEW sample_view AS
            SELECT
                sample_item.sample_item_id,
                sample_file.sample_file_id,
                sample_file.instrument_function_id,
                sample_item.sample_batch_id,
                sample_item.sample_item_name,
                sample_item.t0,
                sample_item.t1,
                sample_file.filename,
                sample_file.instrument,
                sample_file.method_file,
                sample_item.sample_item_type,
                sample_item.sample_item_attributes,
                sample_item.filter_id,
                sample_file.length,
                sample_item.tic,
                sample_item.polarity,
                sample_file.range,
                sample_file.mz_calibration,
                sample_file.datetime,
                sample_file.datetime_utc,
                sample_item.sample_item_utc_created,
                sample_item.sample_item_utc_modified
            FROM
                sample_item
            JOIN
                sample_file ON sample_item.filename = sample_file.filename
            """
        )
    )


if __name__ == "__main__":
    asyncio.run(run())
