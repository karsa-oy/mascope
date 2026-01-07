"""
Migration v41: Establish FK relationship between sample_item and sample_file.

This migration transforms sample_item from filename-based associations to proper
foreign key relationships using SQLAlchemy models as the source of truth.

Changes:
- Add sample_item.sample_file_id (FK to sample_file.sample_file_id)
- Remove sample_item.filename column fomr sample_item table
- Recreate sample_file with corrected NOT NULL constraints
- Update sample_view to use FK join
- Add index on sample_file_id for join performance
"""

import asyncio
import os
import shutil

from sqlalchemy import text
from sqlalchemy.schema import CreateIndex, CreateTable

from mascope_backend.db import (
    SampleFile,
    SampleItem,
    async_session,
    configure_database_engine,
)
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.db.views import Sample
from mascope_backend.runtime import runtime


async def run():
    """Execute migration to v41."""
    await create_db_backup()

    # Setup new database version
    old_version, new_version = 40, 41
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    shutil.copyfile(old_db_path, new_db_path)
    await configure_database_engine(new_version)

    # Apply schema transformations
    runtime.logger.info(
        "Step 1/3: Recreating sample_file with corrected constraints..."
    )
    await recreate_sample_file_table()

    runtime.logger.info("Step 2/3: Adding sample_file_id and recreating sample_item...")
    await add_and_backfill_sample_file_id()
    await recreate_sample_item_table()

    runtime.logger.info("Step 3/3: Recreating sample_view with FK join...")
    async with async_session() as session:
        await session.execute(Sample.create_view())
        await session.commit()

    # db_restore handle validation, orphan cleanup, and index check
    runtime.logger.info("Validating schema and cleaning up orphans...")
    await db_restore()
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed")


async def recreate_sample_file_table():
    """
    Recreate sample_file table using SQLAlchemy model as source of truth.

    This corrects NOT NULL constraints on core columns (instrument, datetime,
    datetime_utc, length, range, polarity) that were incorrectly nullable.

    Uses atomic table swap pattern to avoid FK dependency issues.
    """
    async with async_session() as session:
        # Disable FK enforcement during migration
        await session.execute(text("PRAGMA foreign_keys = OFF;"))

        # --- Drop sample_view (depends on sample_file) ---
        await session.execute(Sample.drop_view())

        # --- Generate CREATE TABLE SQL from model ---
        create_table_sql = str(CreateTable(SampleFile.__table__).compile(session.bind))

        # Modify to use temp table name
        create_table_sql = create_table_sql.replace(
            "CREATE TABLE sample_file", "CREATE TABLE sample_file_new"
        )

        # Create the new table with model-generated schema
        await session.execute(text(create_table_sql))

        # --- Copy all data (no exclusions for sample_file) ---
        await session.execute(
            text(
                """
                INSERT INTO sample_file_new
                SELECT * FROM sample_file;
            """
            )
        )

        # --- Drop old table ---
        await session.execute(text("DROP TABLE sample_file;"))

        # --- Rename new table to final name ---
        await session.execute(
            text("ALTER TABLE sample_file_new RENAME TO sample_file;")
        )

        # --- Create indexes from model ---
        for index in SampleFile.__table__.indexes:
            create_index_sql = str(CreateIndex(index).compile(session.bind))
            runtime.logger.debug(f"Creating index: {index.name}")
            await session.execute(text(create_index_sql))

        # Re-enable FK enforcement
        await session.execute(text("PRAGMA foreign_keys = ON;"))

        await session.commit()
        runtime.logger.info("sample_file table recreated from SQLAlchemy model")


async def add_and_backfill_sample_file_id():
    """Add sample_file_id column and populate from filename join."""
    async with async_session() as session:
        # Add nullable column
        await session.execute(
            text("ALTER TABLE sample_item ADD COLUMN sample_file_id VARCHAR(16);")
        )

        # Backfill from filename join
        result = await session.execute(
            text(
                """
                UPDATE sample_item
                SET sample_file_id = (
                    SELECT sf.sample_file_id 
                    FROM sample_file sf 
                    WHERE sf.filename = sample_item.filename
                );
            """
            )
        )

        await session.commit()
        runtime.logger.info(f"Backfilled {result.rowcount} records")


async def recreate_sample_item_table():
    """
    Recreate sample_item table using SQLAlchemy model as source of truth.
    - Generates table schema from SampleItem model
    - Generates index definitions from SampleItem model
    - Creates sample_view from Sample model
    """
    async with async_session() as session:
        # Disable FK enforcement during migration
        await session.execute(text("PRAGMA foreign_keys = OFF;"))

        # --- Drop sample_view (depends on sample_item) ---
        await session.execute(Sample.drop_view())
        runtime.logger.debug("Dropped sample_view")

        # --- Generate CREATE TABLE SQL from model ---
        create_table_sql = str(CreateTable(SampleItem.__table__).compile(session.bind))

        # Modify to use temp table name
        create_table_sql = create_table_sql.replace(
            "CREATE TABLE sample_item", "CREATE TABLE sample_item_new"
        )

        # Create the new table with model-generated schema
        await session.execute(text(create_table_sql))

        # --- Copy data (filename excluded) ---
        await session.execute(
            text(
                """
                INSERT INTO sample_item_new (
                    sample_item_id, sample_batch_id, sample_file_id,
                    sample_item_name, sample_item_type, locked,
                    sample_item_attributes, filter_id, tic, polarity,
                    ionization_mode_id, t0, t1,
                    sample_item_utc_created, sample_item_utc_modified
                )
                SELECT 
                    sample_item_id, sample_batch_id, sample_file_id,
                    sample_item_name, sample_item_type, locked,
                    sample_item_attributes, filter_id, tic, polarity,
                    ionization_mode_id, t0, t1,
                    sample_item_utc_created, sample_item_utc_modified
                FROM sample_item;
            """
            )
        )

        # --- Drop old table ---
        await session.execute(text("DROP TABLE sample_item;"))

        # --- Rename new table to final name ---
        await session.execute(
            text("ALTER TABLE sample_item_new RENAME TO sample_item;")
        )

        # --- Create indexes from model ---
        for index in SampleItem.__table__.indexes:
            create_index_sql = str(CreateIndex(index).compile(session.bind))
            # Update table name in index SQL
            create_index_sql = create_index_sql.replace(
                "ON sample_item_new", "ON sample_item"
            )
            runtime.logger.debug(f"Creating index: {create_index_sql}")
            await session.execute(text(create_index_sql))

        # Re-enable FK enforcement
        await session.execute(text("PRAGMA foreign_keys = ON;"))

        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
