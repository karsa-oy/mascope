import os
import shutil
import asyncio
from sqlalchemy import insert, select
from mascope_server.db import configure_database_engine, async_session
from mascope_server.db.models import AccessToken, Base
from mascope_server.db.ops.backup import create_db_backup
from mascope_server.runtime import runtime


async def run():
    # Step 1: Create a backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    new_version = 18
    old_db_path = os.path.join(runtime.config.database, "mascope.v17.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database
    await configure_database_engine(new_version)

    # Step 3: Add service_name column to access_token table
    await alter_access_token_table()


async def alter_access_token_table():
    """Add service_name column to access_token table and migrate existing data."""
    runtime.logger.info("Modifying access_token table to add service_name column")

    async with async_session() as session:
        connection = await session.connection()

        # Get existing tokens
        tokens_query = await session.execute(
            select(AccessToken.token, AccessToken.user_id, AccessToken.created_at)
        )
        existing_tokens = tokens_query.all()

        # Store the token data, set existing service_name to 'mascope_sdk'
        token_data = [
            {
                "token": token.token,
                "user_id": token.user_id,
                "created_at": token.created_at,
                "service_name": "mascope_sdk",
            }
            for token in existing_tokens
        ]

        # Drop and recreate the AccessToken table
        await connection.run_sync(
            Base.metadata.drop_all, tables=[AccessToken.__table__]
        )
        await connection.run_sync(
            Base.metadata.create_all, tables=[AccessToken.__table__]
        )

        # Reinsert the tokens with the new service_name column
        if token_data:
            await session.execute(insert(AccessToken).values(token_data))

        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
