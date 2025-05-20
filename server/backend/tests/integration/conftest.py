"""
Test fixtures specific to integration tests.

This module establishes the test database and session infrastructure specifically
for integration tests. It creates an isolated in-memory database just for integration tests,
so that they don't interfere with unit or other test categories.

Key components:
- Integration test-specific database engine and session fixtures
- Database patching to ensure application code uses the test database
- Session fixtures for integration test database access

Integration testing approach:
- Tests how components work together
- Tests more realistic flows through the application
- Verifies subsystem interactions without mocking all dependencies
- Maintains test isolation between categories (unit vs. integration)
"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

import mascope_backend.db as db_module


@pytest.fixture(scope="session")
def async_engine(async_engine_factory):
    """Create an async SQLite in-memory database engine specifically for integration tests.

    This fixture creates an isolated database engine for integration tests, so that
    they don't interfere with other test categories.

    :param async_engine_factory: Factory to create database engines
    :return: SQLAlchemy async engine instance
    :rtype: AsyncEngine
    """
    return async_engine_factory("integration_tests")


@pytest.fixture(scope="session")
def async_session_factory(async_engine):
    """Create an async session factory for integration tests.

    This session factory is used by both session-scoped fixtures (for persistent test data)
    and function-scoped fixtures (for isolated test operations).

    :param async_engine: The SQLAlchemy async engine for integration tests
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
    """Patch the application's database session maker for integration tests.

    This fixture automatically runs for all integration tests so that the application
    connects to the integration test database. It patches the global ASYNC_SESSION_MAKER variable,
    which affects both:
    - async_session() function used in controllers and services
    - get_async_session() dependency used in API routes

    NOTE: The autouse=True parameter makes this patching happens automatically for every integration test,
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
