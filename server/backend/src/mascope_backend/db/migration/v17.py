import asyncio
import os
import shutil

from sqlalchemy import insert

from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.db import Base, Role, async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.runtime import runtime


async def run():
    # Step 1: Create a backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    new_version = 17
    old_db_path = os.path.join(runtime.config.database, "mascope.v16.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    await configure_database_engine(new_version)

    # Step 3: Drop and recreate the Role table, create new AccessToken table
    runtime.logger.info("Modifying role table, creating access_token table.")
    role_access_levels = auth_settings.ROLE_ACCESS_LEVELS
    async with async_session() as session:
        connection = await session.connection()
        await connection.run_sync(
            Base.metadata.drop_all, tables=[Role.__table__]
        )  # Drop the Role table if it exists
        # metadata.create_all() skips existing tables and only creates missing tables.
        await connection.run_sync(Base.metadata.create_all)

        # Step 4: Insert roles dynamically from `ROLE_ACCESS_LEVELS`
        # with explicitly defined role_id mapped to access_level
        await session.execute(
            insert(Role).values(
                [
                    {"role_id": access_level, "role_name": role}
                    for role, access_level in role_access_levels.items()
                ]
            )
        )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
