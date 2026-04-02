"""
Unit tests for the Workspace SQLAlchemy model.
Tests model creation, validation, and relationships.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from mascope_backend.db import SampleBatch, Workspace


@pytest.mark.asyncio
async def test_create_workspace(session):
    """Test creating a workspace with valid data."""
    # Create a workspace with fixed ID
    workspace = Workspace(
        workspace_id="create-test-workspace",
        workspace_name="Create Test Workspace",
        workspace_description="Testing workspace creation",
        workspace_utc_created=datetime.now(timezone.utc),
    )

    # Add to session and commit
    session.add(workspace)
    await session.flush()

    # Retrieve from database
    result = await session.get(Workspace, workspace.workspace_id)

    # Verify workspace was created correctly
    assert result is not None
    assert result.workspace_id == "create-test-workspace"
    assert result.workspace_name == "Create Test Workspace"
    assert result.workspace_description == "Testing workspace creation"
    assert result.workspace_utc_created is not None


@pytest.mark.asyncio
async def test_workspace_name_required(session):
    """Test that workspace_name is required."""
    # Create a workspace without a name
    workspace = Workspace(
        workspace_id="no-name-test-workspace",
        workspace_description="A test workspace without name",
    )

    # Add to session and try to commit
    session.add(workspace)
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_workspace_relationship(session, db_test_workspace, db_test_sample_batch):
    """Test workspace relationship with sample batches."""
    # Verify the sample batch is correctly associated with the workspace
    assert db_test_sample_batch.workspace_id == db_test_workspace.workspace_id

    # Find all batches for this workspace
    stmt = select(SampleBatch).where(
        SampleBatch.workspace_id == db_test_workspace.workspace_id
    )
    result = await session.execute(stmt)
    batches = result.scalars().all()

    # Verify we have at least one batch
    assert len(batches) >= 1

    # Find our test batch
    test_batch = None
    for batch in batches:
        if batch.sample_batch_id == "db-test-batch":
            test_batch = batch
            break

    assert test_batch is not None
    assert test_batch.sample_batch_name == "DB Test Batch"


@pytest.mark.asyncio
async def test_cascade_delete(session):
    """Test that deleting a workspace cascades to sample batches."""
    # Create a workspace for this test
    workspace = Workspace(
        workspace_id="cascade-test-workspace",
        workspace_name="Cascade Test Workspace",
        workspace_utc_created=datetime.now(timezone.utc),
    )
    session.add(workspace)
    await session.flush()

    # Create a sample batch linked to the workspace
    sample_batch = SampleBatch(
        sample_batch_id="cascade-test-batch",
        workspace_id=workspace.workspace_id,
        sample_batch_name="Cascade Test Batch",
        sample_batch_utc_created=datetime.now(timezone.utc),
    )
    session.add(sample_batch)
    await session.flush()

    # Verify the batch exists
    batch_exists = await session.get(SampleBatch, "cascade-test-batch")
    assert batch_exists is not None

    # Delete the workspace
    await session.delete(workspace)
    await session.flush()

    # Check that the sample batch was also deleted
    result = await session.get(SampleBatch, "cascade-test-batch")
    assert result is None
