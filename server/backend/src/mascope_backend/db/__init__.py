"""
Database initialization and configuration module.

This module handles SQLite database connection setup, session management,
and initialization procedures including schema migrations.

Exports:
- Database connection functions (configure_database_engine, async_session, etc.)
- All ORM models from models.py
- All view mappings from views.py
"""

import asyncio
import os
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mascope_backend.db import models
from mascope_backend.db.migration_manager import check_db_migration
from mascope_backend.db.models import *  # noqa: F403, F401 - re-export models
from mascope_backend.db.secrets import postgres_password
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.db.views import Sample
from mascope_backend.runtime import runtime


# Initialize global variables at module load
ASYNC_SESSION_MAKER = None  # Global async session maker
db_cfg = runtime.config.database

# Semaphore to limit concurrent database operations
db_semaphore = asyncio.Semaphore(db_cfg.pool_size)


# Database configuration and session management
async def configure_database_engine(
    version: int | None = None,
    db_type: str | None = None,
):
    """
    Configures the database engine based on type and sets up the
    global session maker using SQLAlchemy's async_sessionmaker.
    This function is called during initialization to establish
    a connection with the database.

    :param version: Required for SQLite, ignored for PostgreSQL
    :param db_type: Override configured type (for explicit control)
    """
    # Use explicit type or fall back to config
    engine_type = db_type or db_cfg.type
    database_url = ""
    if engine_type == "sqlite":
        if version is None:
            raise ValueError("SQLite requires version parameter")

        database_url = db_cfg.get_sqlite_url(version=version)
        runtime.logger.info(
            f"Using SQLite v{version} at {db_cfg.get_sqlite_path(version)}"
        )
    if engine_type == "postgres":
        database_url = db_cfg.get_postgres_url(
            password=postgres_password, env_name=runtime.env.name
        )
        db_name = db_cfg.get_postgres_database_name(env_name=runtime.env.name)
        runtime.logger.info(
            f"Using PostgreSQL at {db_cfg.host}:{db_cfg.port}/{db_name}"
        )

    trace_mode = runtime.config.log_level.lower() == "trace"

    engine = create_async_engine(
        database_url,
        pool_pre_ping=db_cfg.pool_pre_ping,
        echo=trace_mode,
        pool_size=db_cfg.pool_size,
        max_overflow=db_cfg.max_overflow,
        pool_timeout=db_cfg.pool_timeout,
        connect_args=db_cfg.get_connect_args() if engine_type == "sqlite" else {},
    )

    # Enable foreign keys for every SQLite connection, for PostgreSQL it's default
    if engine_type == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            """Enable foreign key constraints for this connection."""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Define the global session maker using async_sessionmaker
    global ASYNC_SESSION_MAKER
    ASYNC_SESSION_MAKER = async_sessionmaker(
        engine, expire_on_commit=db_cfg.expire_on_commit
    )


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
    if ASYNC_SESSION_MAKER is None:
        raise RuntimeError(
            "Database engine is not configured. Call configure_database_engine() first."
        )
    return ASYNC_SESSION_MAKER()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency-injected session for FastAPI route handlers.

    This function yields a session that is automatically managed by FastAPI's
    dependency injection system.
    It ensures that the session is opened at the start of the request and closed
    when the request finishes.

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
    if ASYNC_SESSION_MAKER is None:
        raise RuntimeError(
            "Database engine is not configured. Call configure_database_engine() first."
        )
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
        if db_cfg.type == "sqlite":
            current_version = get_current_db_version()
            await configure_database_engine(version=current_version)
        elif db_cfg.type == "postgres":
            await configure_database_engine()

        await _test_database_connection()

        await _check_async_wal_status()
    except Exception as error:
        runtime.logger.error(f"Database initialization error: {error}")
        raise


async def _test_database_connection():
    """
    Test the database connection by executing a simple query.

    :raises Exception: If the connection cannot be established
    """
    try:
        # Test basic connection
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        runtime.logger.info("Database connection established successfully.")

        # Database-specific checks
        if db_cfg.type == "sqlite":
            async with async_session() as session:
                result = await session.execute(text("PRAGMA foreign_keys"))
                fk_status = "enabled" if result.scalar() == 1 else "disabled"
                runtime.logger.debug(f"SQLite foreign keys status: {fk_status}")
        else:  # postgres
            async with async_session() as session:
                result = await session.execute(text("SELECT version()"))
                pg_version = result.scalar()
                runtime.logger.debug(f"PostgreSQL version: {pg_version}")

                # Test list databases
                result = await session.execute(text("SELECT datname FROM pg_database"))
                databases = [row[0] for row in result.fetchall()]
                runtime.logger.debug(f"Available databases: {databases}\n")

    except Exception as e:
        runtime.logger.error(f"Error while establishing the database connection: {e}")
        raise


async def _check_async_wal_status():
    """
    Check WAL status using configured SQLAlchemy async session.
    """
    try:
        if db_cfg.type == "sqlite":
            async with async_session() as session:
                journal_mode = (
                    await session.execute(text("PRAGMA journal_mode"))
                ).scalar()
                busy_timeout = (
                    await session.execute(text("PRAGMA busy_timeout"))
                ).scalar()

                runtime.logger.debug(
                    f"Database WAL status: journal mode - {journal_mode}, busy timeout - {busy_timeout}ms"
                )
    # PostgreSQL doesn't need WAL checks (it's always WAL)
    except Exception as e:
        runtime.logger.error(f"Error checking database status: {e}")


__all__ = [
    # Connection management
    "configure_database_engine",
    "async_session",
    "get_async_session",
    "init_db",
    # Migration manager
    "check_db_migration",
    # Views
    "Sample",
    # Models (dynamically included from models.__all__)
    *models.__all__,
]
