"""
Migration script for v31: Default Ionization Mechanisms.

This migration adds an 'is_default' boolean column to the ionization_mechanism table
and sets is_default=true for standard acquisition ionization mechanisms.

Schema changes:
- Add is_default boolean field to ionization_mechanism table
- Set is_default=true for: -H-, +Br-, +H+, +(CH4N2O)H+, +CH4N2OH+
"""

import os
import shutil
import asyncio
from sqlalchemy import text, func, update

from mascope_backend.db import configure_database_engine, async_session
from mascope_backend.db.models import IonizationMechanism
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.api.models.ionization_mechanisms.config import (
    ionization_mechanism_config,
)
from mascope_backend.runtime import runtime


async def run():
    """
    Migration to v31: Default Ionization Mechanisms.

    Adds is_default column to ionization_mechanism table and marks
    standard acquisition mechanisms as default.
    """
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 30
    new_version = 31
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    # Configure async engine for new version
    await configure_database_engine(new_version)

    # Step 3: Apply schema migration
    runtime.logger.info("Adding is_default column to ionization_mechanism table")
    await modify_ionization_mechanism_schema()

    # Step 4: Run database maintenance
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully")


async def modify_ionization_mechanism_schema():
    """
    Add is_default boolean column to ionization_mechanism table.

    Sets is_default=true for standard acquisition ionization mechanisms:
    -H-, +Br-, +H+, +(CH4N2O)H+, +CH4N2OH+
    """
    async with async_session() as session:
        # Step 1: Add the is_default column with default value 0
        await session.execute(
            text(
                f"ALTER TABLE ionization_mechanism ADD COLUMN is_default INTEGER NOT NULL DEFAULT {ionization_mechanism_config.DEFAULT_IS_DEFAULT_STATUS}"
            )
        )

        # Step 2: Update specific mechanisms to be default (with trimming)
        default_mechanisms = ionization_mechanism_config.DEFAULT_ACQUISITION_MECHANISMS

        updated_mechanisms = []
        for mechanism in default_mechanisms:
            result = await session.execute(
                update(IonizationMechanism)
                .where(
                    func.trim(IonizationMechanism.ionization_mechanism)
                    == mechanism.strip()
                )
                .values(is_default=True)
            )
            if result.rowcount > 0:
                updated_mechanisms.append(mechanism)

        await session.commit()

        # Step 3: Log results
        runtime.logger.info(
            f"Set {len(updated_mechanisms)} ionization mechanisms as default: {', '.join(updated_mechanisms)}"
        )


if __name__ == "__main__":
    asyncio.run(run())
