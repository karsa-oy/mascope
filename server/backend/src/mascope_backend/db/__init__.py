"""
Database initialization and configuration module.

This module handles PostgreSQL database connection setup, session management,
and initialization procedures.

Exports:
- Database connection functions (configure_database_engine, async_session, etc.)
- All ORM models from models.py
- All view mappings from views.py
"""

import asyncio
import os
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mascope_backend.db import models
from mascope_backend.db.models import *  # noqa: F403, F401 - re-export models
from mascope_backend.db.secrets import postgres_password
from mascope_backend.db.views import Sample
from mascope_backend.runtime import runtime
from mascope_runtime.config import BackendConfig


# Initialize global variables at module load
ASYNC_SESSION_MAKER: async_sessionmaker[AsyncSession] | None = None
assert isinstance(runtime.config, BackendConfig)
db_cfg = runtime.config.database

# Semaphore to limit concurrent database operations
db_semaphore = asyncio.Semaphore(db_cfg.pool_size)


# Database configuration and session management
async def configure_database_engine() -> None:
    """
    Configure the PostgreSQL async engine and global session maker
    using SQLAlchemy's async_sessionmaker.
    This function is called during initialization (once per worker during startup)
    to establish a connection with the database.

    :return: None
    """
    database_url = db_cfg.get_postgres_url(
        password=postgres_password, env_name=runtime.env.name
    )
    db_name = db_cfg.get_postgres_database_name(env_name=runtime.env.name)
    runtime.logger.info(f"Using PostgreSQL at {db_cfg.host}:{db_cfg.port}/{db_name}")

    trace_mode: bool = runtime.config.log_level == "trace"

    engine = create_async_engine(
        database_url,
        pool_pre_ping=db_cfg.pool_pre_ping,
        echo=trace_mode,
        pool_size=db_cfg.pool_size,
        max_overflow=db_cfg.max_overflow,
        pool_timeout=db_cfg.pool_timeout,
    )

    # Define the global session maker using async_sessionmaker
    global ASYNC_SESSION_MAKER
    ASYNC_SESSION_MAKER = async_sessionmaker(
        engine, expire_on_commit=db_cfg.expire_on_commit
    )


async def dispose_engine() -> None:
    """
    Dispose the async engine and close all connection pool connections.
    No-op if the engine has not been configured.

    :return: None
    """
    if ASYNC_SESSION_MAKER is None:
        return
    engine = ASYNC_SESSION_MAKER.kw["bind"]
    await engine.dispose()


def async_session() -> AsyncSession:
    """
    Session getter for manual session management.

    This function returns a new SQLAlchemy session that needs to be manually handled.
    It is useful for scenarios where we need fine-grained control over the session's
    lifecycle, such as flushing manually or performing tasks outside the session block.

    Key points:
    - Requires manual management (you must use `async with`).
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
    - Useful for request-response workflows where session lifecycle should be automated.

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
async def init_db() -> None:
    """
    Initialize database connection for a worker process.

    This function is called by each worker during startup.
    It configures the database engine for this worker's connection pool.

    :raises Exception: If engine configuration or connection test fails
    :return: None
    """
    try:
        await configure_database_engine()
        await _test_database_connection()
        _log_pool_configuration()
    except Exception as error:
        runtime.logger.error(f"Database initialization error: {error}")
        raise


async def _test_database_connection() -> None:
    """
    Test connection and log PostgreSQL version.

    :raises Exception: If the connection cannot be established
    :return: None
    """
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT version()"))
            pg_version = result.scalar()
            runtime.logger.info(
                f"PostgreSQL connection established successfully. Version: {pg_version}"
            )

            result = await session.execute(text("SELECT datname FROM pg_database"))
            databases = [row[0] for row in result.fetchall()]
            runtime.logger.debug(f"Available databases: {databases}")
    except Exception as e:
        runtime.logger.error(f"Database connection failed: {e}")
        raise


def _log_pool_configuration() -> None:
    """
    Log connection pool configuration for this worker.

    :return: None
    """
    if ASYNC_SESSION_MAKER is None:
        return
    try:
        engine = ASYNC_SESSION_MAKER.kw["bind"]
        worker_pid = os.getpid()

        runtime.logger.debug(
            f"Worker {worker_pid} pool config: "
            f"size={engine.pool.size()}, "
            f"max_overflow={engine.pool._max_overflow}, "
            f"timeout={engine.pool._timeout}s"
        )
    except Exception as e:
        runtime.logger.debug(f"Could not log pool configuration: {e}")


__all__ = [
    # Connection management
    "configure_database_engine",
    "dispose_engine",
    "async_session",
    "get_async_session",
    "init_db",
    # Views
    "Sample",
    # Models (dynamically included from models.__all__)
    *models.__all__,
]
