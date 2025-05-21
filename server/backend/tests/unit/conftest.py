"""
Test fixtures specific to unit tests.

This module establishes the test database and session infrastructure specifically
for unit tests. It creates an isolated in-memory database just for unit tests
so that they don't interfere with integration or other test categories.

Key components:
- Unit test-specific database engine and session fixtures
- Database patching to set application code to use the test database
- Session factory fixtures for unit test database access

Unit testing approach:
- Tests individual components in isolation from the rest of the system
- Mocks external dependencies
- Fast, focused tests for specific functionality
- Independent tests with minimal shared state
"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

import mascope_backend.db as db_module


@pytest.fixture(scope="session")
def async_engine(async_engine_factory):
    """Create an async SQLite in-memory database engine specifically for unit tests.

    This fixture creates an isolated database engine for unit tests, so that
    they don't interfere with other test categories.

    :param async_engine_factory: Factory to create database engines
    :return: SQLAlchemy async engine instance
    :rtype: AsyncEngine
    """
    return async_engine_factory("unit_tests")


@pytest.fixture(scope="session")
def async_session_factory(async_engine):
    """Create an async session factory for unit tests.

    This session factory is used by both session-scoped fixtures (for persistent test data)
    and function-scoped fixtures (for isolated test operations).

    :param async_engine: The SQLAlchemy async engine for unit tests
    :type async_engine: AsyncEngine
    :return: Session factory for creating database sessions
    :rtype: async_sessionmaker
    """
    return async_sessionmaker(
        async_engine,
        expire_on_commit=False,  # Keeps objects usable after commit without requerying
        autoflush=False,  # Prevents automatic DB synchronization for more explicit control in tests
    )


@pytest.fixture(scope="session", autouse=True)
def patch_db(async_session_factory):
    """Patch the application's database session maker for unit tests.

    This fixture automatically runs for all unit tests so that the application
    connects to the unit test database. It patches the global ASYNC_SESSION_MAKER variable,
    which affects both:
    - async_session() function used in controllers and services
    - get_async_session() dependency used in API routes

    NOTE: The autouse=True parameter makes this patching happens automatically for every unit test,
    preventing the need to explicitly include this fixture in each test function.

    Without this patching  fixture, application code that directly calls async_session() would try
    to use the real database connection, which would either be unavailable or risk
    damaging real data.

    :param async_session_factory: The test session factory
    :type async_session_factory: async_sessionmaker
    """
    # Store the original session maker to restore it later
    original_session_maker = db_module.ASYNC_SESSION_MAKER

    # Replace with our test session factory
    db_module.ASYNC_SESSION_MAKER = async_session_factory

    yield

    # Restore the original session maker
    db_module.ASYNC_SESSION_MAKER = original_session_maker
