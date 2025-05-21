"""
Provides fixtures for database unit testing.
Includes model factory functions, database session with transaction isolation,
and helpers for testing database models in isolation.
"""

import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def session(async_session_factory):
    """Create a test session with proper transaction management for unit tests.

    This fixture has function scope to provide an isolated session for each test function,
    particularly useful for unit tests that need to manipulate data independently.
    Changes made to the database are visible within the test but don't affect other tests.

    :param async_session_factory: Factory for creating sessions
    :type async_session_factory: async_sessionmaker
    :yield: SQLAlchemy async session
    :rtype: AsyncSession
    """
    async with async_session_factory() as session:
        yield session
        # The session will be closed when the fixture is torn down
