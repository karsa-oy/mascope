"""
Migration script for v40: Simplify and update ionization mechanisms.

This migration removes 'is_default' and 'reagent' columns from the ionization_mechanism table.
Additionally, it updates abstraction ionization mechanisms to reflect changes in formula parsing logic.
E.g. "-H-" is changed to "-H+" to denote deprotonation, according to standard chemical notation.

Schema changes:
- 'is_default' and 'reagent' fields removed from the 'ionization_mechanism' table
"""

import asyncio
import os
import shutil

from sqlalchemy import func, text, update

from mascope_backend.db import (
    IonizationMechanism,
    async_session,
    configure_database_engine,
)
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.runtime import runtime


async def run():
    """
    Migration to v40: Edit Ionization Mechanisms table schema.

    - Remove "is_default" and "reagent" columns from ionization_mechanism table.
    - Change "-H-" mechanism to "-H+" due to updated formula parsing logic.
    """
    # Create backup before migration
    await create_db_backup()

    # Setup new database version
    old_version = 39
    new_version = 40
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    # Configure async engine for new version
    await configure_database_engine(new_version)

    # Apply schema migration
    runtime.logger.info("Modifying 'ionization_mechanism' table")
    await modify_ionization_mechanism_schema()

    # Run database maintenance
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully")


async def modify_ionization_mechanism_schema():
    """
    Remove is_default and reagent columns from ionization_mechanism table.
    Also, update specific ionization mechanisms to reflect new parsing logic.
    """
    async with async_session() as session:
        # Disable FK enforcement during table recreation
        await session.execute(text("PRAGMA foreign_keys = OFF;"))

        # Create a backup of the ionization_mechanism table
        await session.execute(
            text(
                """
                CREATE TABLE ionization_mechanism_backup AS
                SELECT * FROM ionization_mechanism;
            """
            )
        )

        # Drop original table
        await session.execute(text("DROP TABLE ionization_mechanism;"))

        # Recreate table using SQLAlchemy model
        connection = await session.connection()
        await connection.run_sync(IonizationMechanism.__table__.create)

        # Migrate data with new schema (excluding is_default and reagent)
        await session.execute(
            text(
                """
                INSERT INTO ionization_mechanism (
                    ionization_mechanism_id, ionization_mechanism_polarity,
                    ionization_mechanism
                )
                SELECT 
                    ionization_mechanism_id, ionization_mechanism_polarity,
                    ionization_mechanism
                FROM ionization_mechanism_backup;
            """
            )
        )

        # Clean up backup table
        await session.execute(text("DROP TABLE ionization_mechanism_backup;"))

        # Re-enable FK enforcement
        await session.execute(text("PRAGMA foreign_keys = ON;"))

        # Update ionization mechanisms as per new parsing logic
        result = await session.execute(
            update(IonizationMechanism)
            .where(
                IonizationMechanism.ionization_mechanism.like("-%"),
                func.length(IonizationMechanism.ionization_mechanism) > 1,
            )
            .values(
                ionization_mechanism=(
                    func.substr(
                        IonizationMechanism.ionization_mechanism,
                        1,
                        func.length(IonizationMechanism.ionization_mechanism) - 1,
                    )
                    + "+"
                )
            )
        )
        await session.commit()
        updated_mechanisms = result.fetchall()

        runtime.logger.info(
            f"Updated {len(updated_mechanisms)} ionization mechanisms: {', '.join(updated_mechanisms)}"
        )


if __name__ == "__main__":
    asyncio.run(run())
