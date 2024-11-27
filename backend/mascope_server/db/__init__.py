import os
import re
import inspect
from importlib import import_module
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from mascope_server.runtime import runtime


# Initialize global variables at module load
ASYNC_SESSION_MAKER = None  # Global async session maker
db_dir = runtime.config.database


# Database utility functions
def get_available_db_version():
    migrations_dir = os.path.join(os.path.dirname(__file__), "migration")
    files = os.listdir(migrations_dir)
    migrations = [f for f in files if re.search("v[0-9]+.py", f)]
    versions = [int(re.search("[0-9]+", migration).group()) for migration in migrations]
    return max(versions)


def get_current_db_version():
    v = 0
    if os.path.exists(runtime.config.database):
        files = os.listdir(runtime.config.database)
        databases = [f for f in files if re.search("mascope.v[0-9]+.db", f)]
        versions = [
            int(re.search("[0-9]+", database).group()) for database in databases
        ]
        if len(versions) > 0:
            v = max(versions)
    return v


# Migration functions
async def run_migration_script(migration):
    """
    Executes a migration script, handling both synchronous and asynchronous run functions.
    """
    # Check if the migration's 'run' function is a coroutine
    if inspect.iscoroutinefunction(migration.run):
        # If it is a coroutine, await its execution
        runtime.logger.info("Running asynchronous migration script.")
        await migration.run()
    else:
        # Otherwise, run it as a synchronous function
        runtime.logger.info("Running synchronous migration script.")
        migration.run()


async def migrate(current_version, target_version):
    runtime.logger.info("Executing migration pathway")
    if current_version == 0 and not os.path.exists(db_dir):
        os.mkdir(db_dir)
    while current_version < target_version:
        next_version = current_version + 1
        try:
            migration = import_module(f"mascope_server.db.migration.v{next_version}")
        except Exception as error:
            runtime.logger.error(error)
        migration_label = f"from v{current_version} to v{next_version}"
        runtime.logger.info(f"Attempting to migrate mascope database {migration_label}")
        try:
            await run_migration_script(migration)
        except Exception as error:
            runtime.logger.error(f"Migration {migration_label} failed!")
            failed_db_path = os.path.join(db_dir, f"mascope.v{next_version}.db")
            debug_db_path = os.path.join(db_dir, "mascope.debug.db")
            if os.path.exists(failed_db_path):
                os.rename(failed_db_path, debug_db_path)
            runtime.logger.error(error)
            runtime.logger.error(
                f"A copy failed target database is found at {debug_db_path}"
            )
            raise RuntimeError("Database migration failed")
        else:
            runtime.logger.info(f"Migration {migration_label} succeded!")
            current_version = get_current_db_version()
    if current_version == target_version:
        runtime.logger.info("Migration pathway succesful: database is now up-to-date.")
    return current_version


# Database configuration and session management
async def configure_database_engine(version):
    """
    Configures the database engine and sets up the global session maker using SQLAlchemy's async_sessionmaker.
    This function is called during initialization to establish a connection with the database.

    :param version: The current version of the database to configure the connection.
    :type version: int
    """
    db_path = os.path.join(db_dir, f"mascope.v{version}.db")

    # Define the database URL using SQLite and async mode
    database_url = f"sqlite+aiosqlite:///{db_path}"

    #  Enable detailed logging if trace mode is enabled
    trace_mode = runtime.config.log_level.lower() == "trace"

    # Create the async engine for SQLAlchemy
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,  # Check connection liveness before using a connection from the pool
        echo=trace_mode,  # Enable logging of all SQL queries for trace debugging purposes
        connect_args={
            "timeout": 15
        },  # Set a timeout of 15 seconds for establishing connections and waiting for table locks
    )

    # Define the global session maker using async_sessionmaker
    global ASYNC_SESSION_MAKER
    ASYNC_SESSION_MAKER = async_sessionmaker(engine, expire_on_commit=False)


def async_session() -> AsyncSession:
    """
    Session getter for manual session management.

    This function returns a new SQLAlchemy session that needs to be manually handled.
    It is useful for scenarios where we need fine-grained control over the session's lifecycle,
    such as flushing manually or performing tasks outside the session block.

    Key points:
    - Requires manual management (you must use `async with`).
    - Offers flexibility for doing tasks outside the session (e.g., logging or computation).
    - Useful for batch processing where manual flushes or commits are required.

    Example usage:
        async with async_session() as session:
            # Perform operations within the session block
            session.flush()  # Optionally flush without committing

    :return: A new SQLAlchemy async session.
    :rtype: AsyncSession
    """
    return ASYNC_SESSION_MAKER()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency-injected session for FastAPI route handlers.

    This function yields a session that is automatically managed by FastAPI's dependency injection system.
    It ensures that the session is opened at the start of the request and closed when the request finishes.

    Key points:
    - Automatically manages session lifecycle (opened and closed at the correct time).
    - Integrates with FastAPI `Depends()` to inject the session into routes.
    - Suitable for typical request-response workflows where session lifecycle should be automated.

    Example usage in a FastAPI route:
        from fastapi import Depends

        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_async_session)):
            # Perform operations within the session

    :yield: Yields an active SQLAlchemy session for database interactions.
    :rtype: AsyncGenerator[AsyncSession, None]
    """
    async with ASYNC_SESSION_MAKER() as session:
        yield session


# Initialization and main interface functions
async def init_db():
    """
    Initialize the database by checking its version and performing any necessary migrations.

    This function determines the current database version, compares it to the target version,
    and applies the necessary migration scripts to bring the database up to date. It also
    configures the database engine and tests the connection.

    Steps:
    1. Determine the current and target database versions.
    2. Apply database migrations if necessary.
    3. Configure the database engine for the detected version.
    4. Test the database connection to ensure it is properly initialized.

    :raises Exception: If any error occurs during the migration or initialization process.
    """
    try:
        runtime.logger.info("Initializing mascope database")

        # Get the current and target database versions
        current_version = get_current_db_version()
        target_version = get_available_db_version()

        runtime.logger.info(f"Detected mascope database version: v{current_version}")

        if current_version == target_version:
            runtime.logger.info("No database migration needed.")
            await configure_database_engine(current_version)
        else:
            runtime.logger.info(f"This version of mascope requires: v{target_version}")
            await migrate(current_version, target_version)
    except Exception as error:
        runtime.logger.error(error)

    # Test the database connection after initialization
    await test_database_connection()


async def test_database_connection():
    try:
        # create a new session and close it
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        runtime.logger.info("Database connection established successfully.")
    except Exception as e:
        runtime.logger.error(f"Error while establishing the database connection: {e}")
