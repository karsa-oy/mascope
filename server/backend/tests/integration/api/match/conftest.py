"""
Fixtures for match integration tests.

The aggregation controller reads samples through the ``sample_view`` database
VIEW, which ``Base.metadata.create_all`` does not create (it lives in a
separate mapper registry and is normally created only by the initial Alembic
migration). Create it here for this package's tests; other integration
packages are unaffected by the extra view.
"""

import pytest_asyncio
from sqlalchemy import text

from mascope_backend.db import Sample


@pytest_asyncio.fixture(scope="session", autouse=True)
async def sample_view(async_engine):
    """Create the sample_view VIEW in the integration test database."""
    async with async_engine.begin() as conn:
        await conn.execute(text(Sample.drop_view()))
        await conn.execute(text(Sample.create_view()))
