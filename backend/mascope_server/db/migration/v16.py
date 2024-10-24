import os
import shutil
import asyncio
from mascope_server.db import configure_database_engine
from mascope_server.db.ops.backup import create_db_backup
from mascope_server.db.ops.restore import db_restore
from mascope_server.db.ops.maintenance import db_maintenance
from mascope_server.runtime import runtime


async def run():
    """
    Asynchronous migration script for v16.
    - Creates a backup of the database.
    - Sets up a new database.
    - Restores the correct table schemas.
    - Runs maintenance on the updated database.
    """
    await create_db_backup()

    # Step 1: Setup new database version
    new_version = 16
    old_db_path = os.path.join(runtime.config.database, "mascope.v15.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy the old database to create the new version
    shutil.copyfile(old_db_path, new_db_path)

    # Reconfigure the database engine to point to the new v16 database
    configure_database_engine(new_version)

    # Step 2: Restore the schema of the ionization_mechanism table with its
    # updated definition (nullable reagent, unique constraint)
    await db_restore(tables_to_restore=["ionization_mechanism"])

    # Steps to Extend database schema to include method_file #559

    # Step 4: Run database maintenance (vacuum, analyze, integrity check)
    await db_maintenance()


if __name__ == "__main__":
    asyncio.run(run())
