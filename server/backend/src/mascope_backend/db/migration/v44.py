"""
Migration v44: Drop match_isotope_similarity column and set batches to rematch.
"""

import asyncio
import os
import shutil

from sqlalchemy import text, update

from mascope_backend.db import SampleBatch, async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


async def run():
    """Execute migration to v44."""
    await create_db_backup()

    old_version, new_version = 43, 44
    old_db_path = os.path.join(
        runtime.config.database.data_dir, f"mascope.v{old_version}.db"
    )
    new_db_path = os.path.join(
        runtime.config.database.data_dir, f"mascope.v{new_version}.db"
    )

    shutil.copyfile(old_db_path, new_db_path)
    await configure_database_engine(new_version)

    await drop_match_isotope_similarity()
    await set_batches_to_rematch_status()

    runtime.logger.info("Validating schema and cleaning up orphans...")
    await db_restore()
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed")


async def drop_match_isotope_similarity() -> None:
    """Drop the match_isotope_similarity column from match_isotope table."""
    runtime.logger.info("Dropping match_isotope.match_isotope_similarity column...")

    async with async_session() as session:
        await session.execute(text("PRAGMA foreign_keys = OFF;"))
        await session.execute(
            text("ALTER TABLE match_isotope DROP COLUMN match_isotope_similarity;")
        )
        await session.execute(text("PRAGMA foreign_keys = ON;"))
        await session.commit()

    runtime.logger.info("Column match_isotope_similarity dropped.")


async def set_batches_to_rematch_status() -> None:
    """Set all existing sample batches to 'rematch' status."""
    runtime.logger.info("Setting all sample batches to 'rematch' status...")

    async with async_session() as session:
        await session.execute(update(SampleBatch).values(status="rematch"))
        await session.commit()

    runtime.logger.info("All sample batches set to 'rematch' status.")


if __name__ == "__main__":
    asyncio.run(run())
