"""
Migration script for v30: Acquisition Workspace System Implementation.

This migration implements the unified type-based approach to distinguish acquisition
vs analysis instances across the data hierarchy (workspaces → batches → samples).

Schema changes:
- Add workspace_type, instrument, locked fields to workspace table
- Add sample_batch_type, locked fields to sample_batch table
- Add locked field to sample_item table
- Update sample_view to reflect schema changes
- Set all existing instances to ANALYSIS type (default)
"""

import os
import shutil
import asyncio
from sqlalchemy import text

from mascope_backend.db import configure_database_engine, async_session
from mascope_backend.db.models import Workspace, SampleBatch, SampleItem
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


async def run():
    """
    Migration to v30: Acquisition Workspace System.

    This migration adds the necessary fields and constraints to support
    the acquisition vs analysis type system across workspaces, batches, and samples.
    """
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 29
    new_version = 30
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    # Configure async engine for new version
    await configure_database_engine(new_version)

    # Step 3: Apply schema migrations
    runtime.logger.info("Applying schema changes for acquisition workspace system")
    await modify_workspace_schema()
    await modify_sample_batch_schema()
    await modify_sample_item_schema()
    await update_sample_view()

    # restore to fix inconsistencies in TargetCollection target_collection_type default value "'TARGETS'" -> 'TARGETS'
    await db_restore()

    # Step 4: Run database maintenance
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully")


async def modify_workspace_schema():
    """
    Add workspace_type, instrument, and locked fields to workspace table.

    Uses modern SQLAlchemy approach with backup-and-recreate pattern for safety.
    Sets all existing workspaces to ANALYSIS type with unlocked status.
    """
    async with async_session() as session:
        # Step 1: Create backup table with existing data
        await session.execute(
            text(
                """
                CREATE TABLE workspace_backup AS
                SELECT * FROM workspace;
            """
            )
        )

        # Step 2: Drop original table
        await session.execute(text("DROP TABLE workspace;"))

        # Step 3: Recreate table using SQLAlchemy model
        connection = await session.connection()
        await connection.run_sync(Workspace.__table__.create)

        # Step 4: Migrate data with new default values
        await session.execute(
            text(
                """
                INSERT INTO workspace (
                    workspace_id, workspace_name, workspace_description,
                    workspace_type, locked, instrument, icon,
                    workspace_utc_created, workspace_utc_modified
                )
                SELECT 
                    workspace_id, workspace_name, workspace_description,
                    'ANALYSIS' as workspace_type,
                    0 as locked,
                    NULL as instrument,
                    NULL as icon,
                    workspace_utc_created, workspace_utc_modified
                FROM workspace_backup;
            """
            )
        )

        # Step 5: Clean up backup table
        await session.execute(text("DROP TABLE workspace_backup;"))

        await session.commit()
        runtime.logger.info("Workspace table schema updated successfully")


async def modify_sample_batch_schema():
    """
    Add sample_batch_type and locked fields to sample_batch table.

    Sets all existing sample batches to ANALYSIS type with unlocked status
    and +- polarity (suitable for both positive and negative samples).
    """
    async with async_session() as session:
        # Step 1: Create backup table
        await session.execute(
            text(
                """
                CREATE TABLE sample_batch_backup AS
                SELECT * FROM sample_batch;
            """
            )
        )

        # Step 2: Drop original table
        await session.execute(text("DROP TABLE sample_batch;"))

        # Step 3: Recreate table using SQLAlchemy model
        connection = await session.connection()
        await connection.run_sync(SampleBatch.__table__.create)

        # Step 4: Migrate data with new fields
        await session.execute(
            text(
                """
                INSERT INTO sample_batch (
                    sample_batch_id, workspace_id, sample_batch_name, 
                    sample_batch_description, sample_batch_type, locked, polarity,
                    build_params, sample_batch_utc_created, sample_batch_utc_modified
                )
                SELECT 
                    sample_batch_id, workspace_id, sample_batch_name,
                    sample_batch_description, 
                    'ANALYSIS' as sample_batch_type,
                    0 as locked,
                    '+-' as polarity,
                    build_params, sample_batch_utc_created, sample_batch_utc_modified
                FROM sample_batch_backup;
            """
            )
        )

        # Step 5: Clean up backup table
        await session.execute(text("DROP TABLE sample_batch_backup;"))

        await session.commit()
        runtime.logger.info("Sample batch table schema updated successfully")


async def modify_sample_item_schema():
    """
    Add locked field to sample_item table.

    Sets all existing sample items to unlocked status.
    """
    async with async_session() as session:
        # Step 1: Create backup table
        await session.execute(
            text(
                """
                CREATE TABLE sample_item_backup AS
                SELECT * FROM sample_item;
            """
            )
        )

        # Step 2: Drop original table
        await session.execute(text("DROP TABLE sample_item;"))

        # Step 3: Recreate table using SQLAlchemy model
        connection = await session.connection()
        await connection.run_sync(SampleItem.__table__.create)

        # Step 4: Migrate data with new locked field
        await session.execute(
            text(
                """
                INSERT INTO sample_item (
                    sample_item_id, sample_batch_id, filename, sample_item_name,
                    sample_item_type, locked, sample_item_attributes,
                    sample_item_utc_created, sample_item_utc_modified,
                    filter_id, tic, polarity, t0, t1
                )
                SELECT 
                    sample_item_id, sample_batch_id, filename, sample_item_name,
                    sample_item_type, 
                    0 as locked,
                    sample_item_attributes, sample_item_utc_created, sample_item_utc_modified,
                    filter_id, tic, polarity, t0, t1
                FROM sample_item_backup;
            """
            )
        )

        # Step 5: Clean up backup table
        await session.execute(text("DROP TABLE sample_item_backup;"))

        await session.commit()
        runtime.logger.info("Sample item table schema updated successfully")


async def update_sample_view():
    """
    Update the sample_view to reflect the new schema changes.

    This view joins sample_item and sample_file tables and should include
    the new fields that are relevant for sample data access.
    """
    async with async_session() as session:
        # Step 1: Drop existing view
        await session.execute(text("DROP VIEW IF EXISTS sample_view;"))

        # Step 2: Recreate view with updated columns
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
                    sample_file.filename,
                    sample_file.instrument,
                    sample_item.sample_item_type,
                    sample_item.locked,
                    sample_file.method_file,
                    sample_item.t0,
                    sample_item.t1,
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
                    sample_file ON sample_item.filename = sample_file.filename;
            """
            )
        )

        await session.commit()
        runtime.logger.info("Sample view updated successfully")


if __name__ == "__main__":
    asyncio.run(run())
