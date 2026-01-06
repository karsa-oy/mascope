"""
Migration script for v33: Remove match_interference table and interference columns.
"""

import asyncio
import os
import shutil

from sqlalchemy import text

from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.runtime import runtime


# List of tables and columns to drop
DROP_TABLES = ["match_interference"]
DROP_COLUMNS = ["sample_peak_interference_sum"]

# Tables to alter
ALTER_TABLES = [
    "match_sample",
    "match_collection",
    "match_compound",
    "match_ion",
    # Add any other tables that have these columns
]


async def run():
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 32
    new_version = 33
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)
    runtime.logger.info(
        "Starting v33 migration: removing interference columns and table."
    )

    async with async_session() as session:
        # 1. Drop match_interference table
        for table in DROP_TABLES:
            await session.execute(text(f"DROP TABLE IF EXISTS {table};"))
            runtime.logger.info(f"Dropped table: {table}")

        # 2. Remove columns from tables
        for table in ALTER_TABLES:
            for col in DROP_COLUMNS:
                try:
                    await session.execute(
                        text(f"ALTER TABLE {table} DROP COLUMN {col};")
                    )
                    runtime.logger.info(f"Dropped column {col} from {table}")
                except Exception as e:
                    runtime.logger.warning(
                        f"Could not drop column {col} from {table}: {e}"
                    )

        await session.commit()
        runtime.logger.info("v33 migration completed.")


if __name__ == "__main__":
    asyncio.run(run())
