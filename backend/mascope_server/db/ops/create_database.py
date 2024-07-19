import os
import asyncio
from mascope_server.db import (
    get_available_db_version,
    get_current_db_version,
    create_db_backup,
    configure_database_engine,
    async_session,
)
from mascope_server.api.models.models import Base
import mascope_runtime as runtime

from mascope_server.config import config

logger = runtime.logger.service("backend")


async def create_database():
    last_version = get_available_db_version()
    existing_version = get_current_db_version()
    # Check if the last version matches the existing version
    if last_version == existing_version:
        logger.warning(
            f"Existing database with the last available version {existing_version} detected, creating a backup."
        )
        db_path = os.path.join(
            config.server.database, f"mascope.v{existing_version}.db"
        )
        if not os.path.exists(db_path):
            logger.error("Existing database file not found.")
            return
        create_db_backup(db_path, "create_database")
        os.remove(db_path)
        logger.info(f"Removed previous database file: {db_path}")

    # configure the database connection which will create a new database file (also updates the global async_session)
    configure_database_engine(last_version)

    # Create all tables in the database according to models defined in the Base
    async with async_session() as session:
        # Acquire a connection
        connection = await session.connection()

        # Create all tables according to the Base metadata
        await connection.run_sync(Base.metadata.create_all)
        await session.commit()

    logger.info(f"New database mascope.v{last_version} created successfully.")


def run():
    asyncio.run(create_database())


if __name__ == "__main__":
    run()
