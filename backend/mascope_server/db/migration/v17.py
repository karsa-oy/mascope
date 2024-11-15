import os
import shutil
import asyncio
from sqlalchemy import delete, insert
from mascope_server.db import configure_database_engine, async_session
from mascope_server.db.models import Base, Role
from mascope_server.db.ops.backup import create_db_backup
from mascope_server.runtime import runtime
from mascope_server.api.new.auth.config import auth_settings


async def run():
    # Create the backup before migration
    await create_db_backup()

    # Step 1: Setup new database version
    new_version = 17
    old_db_path = os.path.join(runtime.config.database, "mascope.v16.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    configure_database_engine(new_version)

    # Step 2: Create new AccessToken table
    runtime.logger.info("Creating access_token table.")
    async with async_session() as session:
        # Acquire connection
        connection = await session.connection()

        # metadata.create_all() skips existing tables and only creates missing tables.
        await connection.run_sync(Base.metadata.create_all)

        # Step 3: Create roles dynamically from `ROLE_ACCESS_LEVELS`
        runtime.logger.info("Inserting roles into the database.")
        role_access_levels = auth_settings.ROLE_ACCESS_LEVELS

        # Clear existing roles before inserting new ones
        await session.execute(delete(Role))

        # Insert roles with explicitly defined role_id mapped to access_level
        await session.execute(
            insert(Role).values(
                [
                    {"role_id": access_level, "name": role}
                    for role, access_level in role_access_levels.items()
                ]
            )
        )

        # Commit the transaction
        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
