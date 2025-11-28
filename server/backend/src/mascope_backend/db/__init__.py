"""
Database initialization and configuration module.

This module handles SQLite database connection setup, session management,
and initialization procedures including schema migrations.
"""

import asyncio
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text
from mascope_backend.db.config import db_config
from mascope_backend.db.migration_manager import check_db_migration
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.runtime import runtime


# Initialize global variables at module load
ASYNC_SESSION_MAKER = None  # Global async session maker
db_dir = runtime.config.database

# Semaphore to limit concurrent database operations
db_semaphore = asyncio.Semaphore(db_config.POOL_SIZE)


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
        pool_pre_ping=db_config.POOL_PRE_PING,
        echo=trace_mode,
        pool_size=db_config.POOL_SIZE,
        max_overflow=db_config.MAX_OVERFLOW,
        pool_timeout=db_config.POOL_TIMEOUT,
        connect_args=db_config.connect_args,
    )

    # Define the global session maker using async_sessionmaker
    global ASYNC_SESSION_MAKER
    ASYNC_SESSION_MAKER = async_sessionmaker(
        engine, expire_on_commit=db_config.EXPIRE_ON_COMMIT
    )


def async_session() -> AsyncSession | None:
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
    :rtype: AsyncSession | None
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
    async with db_semaphore:
        async with ASYNC_SESSION_MAKER() as session:
            yield session


# Initialization and main interface functions
async def init_db():
    """
    Initialize database connection for a worker process.

    This function is called by each worker during startup.
    It configures the database engine for this worker's connection pool.

    :raises Exception: If engine configuration or connection test fails
    """
    try:
        current_version = get_current_db_version()
        await configure_database_engine(current_version)

        await test_database_connection()

        await check_async_wal_status()
    except Exception as error:
        runtime.logger.error(f"Database initialization error: {error}")
        raise


async def test_database_connection():
    """
    Test the database connection by executing a simple query.

    :raises Exception: If the connection cannot be established
    """
    try:
        # create a new session and close it
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        runtime.logger.info("Database connection established successfully.")
    except Exception as e:
        runtime.logger.error(f"Error while establishing the database connection: {e}")
        raise


async def check_async_wal_status():
    """
    Check WAL status using configured SQLAlchemy async session.
    """
    try:
        async with async_session() as session:
            journal_mode = (await session.execute(text("PRAGMA journal_mode"))).scalar()
            busy_timeout = (await session.execute(text("PRAGMA busy_timeout"))).scalar()

            runtime.logger.debug(
                f"Database WAL status: journal mode - {journal_mode}, busy timeout - {busy_timeout}ms"
            )
    except Exception as e:
        runtime.logger.error(f"Error checking async WAL status: {e}")
