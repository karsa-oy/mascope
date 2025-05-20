"""
Global pytest fixtures and factory functions for the entire test suite.

This module provides core testing infrastructure that is shared across all test categories
(unit, integration, etc.). It defines factory fixtures that allow each test category to create
its own isolated testing environment.

Design principles:
- Test isolation: Different test categories (unit, integration) use separate isolated databases
- Reusable components: Core functionality is provided as factories
- Explicit organization: Test fixtures are organized by their scope and purpose
- Fixture dependency chain: Always from narrower scope to wider scope
  (function → class → module → session), never the reverse
"""

import asyncio
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from mascope_backend.db.models import Base


@pytest.fixture(scope="session")
def async_engine_factory():
    """Factory fixture that creates in-memory SQLite engines for different test categories.

    This factory enables different test categories (unit, integration, etc.) to create
    their own isolated in-memory database engines. Each engine gets its own connection pool
    for complete isolation between test categories.

    Usage in category-specific conftest.py files:
        @pytest.fixture(scope="session")
        def async_engine(async_engine_factory):
            return async_engine_factory("unit_tests")  # or "integration_tests", etc.

    :return: Function to create engine instances
    :rtype: callable
    """
    created_engines = []

    def _create_engine(category_name):
        """Create an in-memory SQLite engine for a specific test category.

        :param category_name: Name of the test category (e.g., "unit", "integration")
        :type category_name: str
        :return: Configured AsyncEngine instance
        :rtype: AsyncEngine
        """
        # Create an isolated in-memory database
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # Create all tables
        async def setup_db():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                #  debugging marker to identify database when looking at the SQLite connections
                await conn.execute(
                    text(f"PRAGMA application_id = {hash(category_name) & 0x7FFFFFFF}")
                )

        asyncio.run(setup_db())

        # Keep track of created engines for cleanup
        created_engines.append((engine, category_name))
        return engine

    yield _create_engine

    # Cleanup all engines
    for engine, category in created_engines:

        async def close_engine(eng):
            await eng.dispose()

        asyncio.run(close_engine(engine))
