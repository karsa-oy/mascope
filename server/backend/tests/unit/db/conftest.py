"""
Fixtures for database unit tests.

Provides a function-scoped session for isolated per-test database access.
Each test gets a fresh session; uncommitted state does not leak between tests
because SQLAlchemy closes the session on exit.
"""

import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def session(async_session_factory):
    """Create an isolated database session for a single test function.

    asyncpg requires all session operations to run in the same event loop
    as the engine. With `asyncio_default_test_loop_scope = session` in
    `pytest.ini`, test functions share the session event loop where the
    engine was created, preventing `InterfaceError: another operation is
    in progress` that occurs when loop scopes differ.

    :param async_session_factory: Factory for creating database sessions
    :type async_session_factory: async_sessionmaker
    :yield: SQLAlchemy async session
    :rtype: AsyncSession
    """
    async with async_session_factory() as session:
        yield session
    # The session will be closed when the fixture is torn down
