import os
import shutil
import asyncio
from sqlalchemy import text
from mascope_server.db import configure_database_engine, async_session
from mascope_server.db.ops.backup import create_db_backup
from mascope_server.runtime import runtime


async def run():
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    new_version = 19
    old_db_path = os.path.join(runtime.config.database, "mascope.v18.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    await configure_database_engine(new_version)

    # Add new column resolution to target_isotope table
    runtime.logger.info("Adding resolution column to the target_isotope table.")
    async with async_session() as session:
        await session.execute(
            text(
                "ALTER TABLE target_isotope ADD COLUMN resolution VARCHAR(8) NOT NULL DEFAULT 'low';"
            )
        )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
