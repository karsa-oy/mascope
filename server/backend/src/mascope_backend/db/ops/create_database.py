"""
Utility module for creating a new database from scratch with the latest schema.

It provides two entry points:
- An async function `create_database()` for use by other async code
- A sync function `run()` as the Poetry command entry point
"""

import asyncio
import os

from mascope_backend.db import (
    Base,
    Sample,
    async_session,
    configure_database_engine,
)
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.utils import get_available_db_version, get_current_db_version
from mascope_backend.db.wal.engine import enable_wal_mode
from mascope_backend.runtime import runtime


async def create_database():
    """
    Create a new database with all tables defined in the SQLAlchemy models.

    This function:
    1. Creates all database tables based on the SQLAlchemy models
    2. Creates the sample_view for joining sample_item and sample_file

    Assumes a database connection is already established.

    :return: None
    """
    # Create all tables in the database according to models defined in the Base
    async with async_session() as session:
        # Acquire a connection
        connection = await session.connection()

        # Create all tables from Base metadata
        await connection.run_sync(Base.metadata.create_all)

        # Create the sample_view using the centralized definition
        await connection.execute(Sample.create_view())

        await session.commit()

    runtime.logger.info("New database created successfully.")


async def init_db_and_create():
    """
    Initialize the database configuration and create a new database.

    This function:
    1. Checks if a database with the latest available version already exists.
        When it is not a new runtime environment.
    2. Backs up any existing database before removing it
    3. Configures the database engine with the latest version
    4. Creates a new database with all required tables and views
    5. Enables WAL mode for improved concurrent access

    :return: None
    """
    last_version = get_available_db_version()
    existing_version = get_current_db_version()

    # If database with latest version already exists, back it up and remove it
    if last_version == existing_version:
        runtime.logger.warning(
            f"Existing database with the last available version {existing_version} detected, creating a backup."
        )
        db_path = os.path.join(
            runtime.config.database.data_dir, f"mascope.v{existing_version}.db"
        )
        if not os.path.exists(db_path):
            runtime.logger.error("Existing database file not found.")
            return

        # Create the backup
        await create_db_backup()

        # Remove the old database
        try:
            os.remove(db_path)
            runtime.logger.info(f"Removed previous database file: {db_path}")
        except PermissionError as e:
            runtime.logger.error(f"Failed to remove the database file: {e}")
            return

    # Configure the database engine with the latest version
    # This creates a new database file and establishes the async connection
    await configure_database_engine(last_version)

    # Create all tables defined in the SQLAlchemy models
    await create_database()

    # Enable WAL mode for new databases to support concurrent access
    await enable_wal_mode()

    runtime.logger.info(f"Database mascope.v{last_version} setup completed.")


def run_db_create():
    """
    Synchronous entry point for the Poetry command 'mascope-db-create'.

    Initializes the database configuration and creates a new database.
    """
    asyncio.run(init_db_and_create())


if __name__ == "__main__":
    run_db_create()
