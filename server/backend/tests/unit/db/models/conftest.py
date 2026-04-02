"""
Fixtures for database model tests.
"""

from datetime import datetime, timezone

import pytest_asyncio

from mascope_backend.db import SampleBatch, Workspace


@pytest_asyncio.fixture
async def db_test_workspace(session):
    """Create a workspace for database testing."""
    # Create the workspace
    workspace = Workspace(
        workspace_id="db-test-workspace",
        workspace_name="DB Test Workspace",
        workspace_description="A workspace for DB testing",
        workspace_utc_created=datetime.now(timezone.utc),
    )

    # Add to session
    session.add(workspace)
    await session.flush()

    # Return the workspace
    yield workspace


@pytest_asyncio.fixture
async def db_test_sample_batch(session, db_test_workspace):
    """Create a sample batch linked to db_test_workspace."""
    # Create the batch
    batch = SampleBatch(
        sample_batch_id="db-test-batch",
        workspace_id=db_test_workspace.workspace_id,
        sample_batch_name="DB Test Batch",
        sample_batch_description="A batch for DB testing",
        sample_batch_utc_created=datetime.now(timezone.utc),
    )

    # Add to session
    session.add(batch)
    await session.flush()

    # Return the batch
    yield batch
