"""
Fixtures for database unit tests.

Provides a function-scoped session for per-test database access.
Each test gets a fresh session; state that is flushed but not committed
is discarded when SQLAlchemy closes the session on exit. Committed changes
persist in the shared test database for the remainder of the session —
db model tests should use flush() only and avoid commit() to maintain
test independence.
"""

import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def session(async_session_factory):
    """Create a database session for a single test function.

    Function-scoped so each test starts with a clean transaction context.
    DB model tests use flush() only — committed changes would persist in the
    shared per-category database and could affect later tests.

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
