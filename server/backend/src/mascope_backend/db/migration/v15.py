import asyncio
import os
import shutil

from mascope_backend.db import Base, async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.runtime import runtime


async def run():
    # Create the backup before migration
    await create_db_backup()

    # Step 1: Setup new database version
    new_version = 15
    old_db_path = os.path.join(runtime.config.database, "mascope.v14.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    configure_database_engine(new_version)

    # Step 2: Create new User and Role tables
    runtime.logger.info("Creating User and Role tables.")
    async with async_session() as session:
        # Acquire connection
        connection = await session.connection()

        # metadata.create_all() skips existing tables and only creates missing tables.
        await connection.run_sync(Base.metadata.create_all)

        # Commit the transaction
        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
