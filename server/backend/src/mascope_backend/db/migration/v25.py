"""
Migration script, the script name shows a new database version.
"""

import os
import shutil

from sqlalchemy import select, text

from mascope_backend.api.controllers.match.match_controller import (
    rematch_batches,
)
from mascope_backend.api.models.match.match_pydantic_model import (
    RematchBatchBody,
    RematchBatchesBody,
)
from mascope_backend.db import SampleBatch, async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.runtime import runtime


async def run():
    """
    Execute the database migration
    """
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    old_version = 24
    new_version = 25
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)

    runtime.logger.info(
        "Rename match_isotope_correlation to match_isotope_similarity..."
    )
    await rename_match_isotope_correlation()

    runtime.logger.info(
        "Rematching batches to update the match isotope similarity and the ion match score..."
    )
    await rematch_all_batches()

    # Clean up the database
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully.")


async def rename_match_isotope_correlation():
    """
    Rename the match_isotope_correlation column to match_isotope_similarity.
    """
    async with async_session() as session:
        await session.execute(
            text(
                """
                ALTER TABLE match_isotope
                RENAME COLUMN match_isotope_correlation TO match_isotope_similarity;
                """
            )
        )
        await session.commit()


async def rematch_all_batches():
    """
    Rematch all sample batches to update the match isotope similarity and the ion match score.
    """
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
