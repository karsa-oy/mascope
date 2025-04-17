"""
Migration script for v22 to v23 database migration.
"""

import os
import shutil

from sqlalchemy import select, text
from mascope_backend.api.controllers.match.match_controller import (
    rematch_batches,
)
from mascope_backend.api.models.match.match_pydantic_model import (
    RematchBatchesBody,
    RematchBatchBody,
)
from mascope_backend.db.models import SampleBatch
from mascope_backend.db import (
    async_session,
    configure_database_engine,
)
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.backup import create_db_backup

from mascope_backend.runtime import runtime


async def run():
    """
    Execute the v22 to v23 database migration
    """
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    new_version = 23
    old_db_path = os.path.join(runtime.config.database, "mascope.v22.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)

    runtime.logger.info(
        "Rename sample_peak_intensity_mean to sample_peak_intensity_sum..."
    )
    async with async_session() as session:
        await rename_columns(session)

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

    # Clean up the database
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully.")


async def rename_columns(session):
    """
    Rename columns "sample_peak_intensity_mean": "sample_peak_intensity_sum" in all tables.
    """
    # Define the columns to rename
    old_column, new_column = "sample_peak_intensity_mean", "sample_peak_intensity_sum"

    result = await session.execute(
        text(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        )
    )
    tables = [row[0] for row in result.fetchall()]

    for table in tables:
        # Check if the column exists in the table
        result = await session.execute(
            text(
                f"""
                PRAGMA table_info({table});
                """
            )
        )
        columns = [row[1] for row in result.fetchall()]
        if old_column not in columns:
            continue

        runtime.logger.info(
            f"Renaming column {old_column} to {new_column} in table {table}..."
        )
        await session.execute(
            text(
                f"""
                ALTER TABLE {table}
                RENAME COLUMN {old_column} TO {new_column};
                """
            )
        )
    session.commit()
    runtime.logger.info("Column renaming completed.")
