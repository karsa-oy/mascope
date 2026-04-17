"""
Unit tests for the Workspace SQLAlchemy model.
Tests model creation, validation, and relationships.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from test_utils import gen_test_id

from mascope_backend.db import SampleBatch, Workspace


@pytest.mark.asyncio
async def test_create_workspace(session):
    """Test creating a workspace with valid data."""
    workspace = Workspace(
        workspace_id=gen_test_id(),
        workspace_name="Create Test Workspace",
        workspace_description="Testing workspace creation",
        workspace_utc_created=datetime.now(timezone.utc),
    )
    session.add(workspace)
    await session.flush()

    result = await session.get(Workspace, workspace.workspace_id)

    assert result is not None
    assert result.workspace_id == workspace.workspace_id
    assert result.workspace_name == "Create Test Workspace"
    assert result.workspace_description == "Testing workspace creation"
    assert result.workspace_utc_created is not None


@pytest.mark.asyncio
async def test_workspace_name_required(session):
    """Test that workspace_name is required."""
    workspace = Workspace(
        workspace_id=gen_test_id(),
        workspace_description="A test workspace without name",
    )
    session.add(workspace)
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_workspace_relationship(session, db_test_workspace, db_test_sample_batch):
    """Test workspace relationship with sample batches."""
    assert db_test_sample_batch.workspace_id == db_test_workspace.workspace_id

    stmt = select(SampleBatch).where(
        SampleBatch.workspace_id == db_test_workspace.workspace_id
    )
    result = await session.execute(stmt)
    batches = result.scalars().all()

    assert len(batches) >= 1

    test_batch = next(
        (
            b
            for b in batches
            if b.sample_batch_id == db_test_sample_batch.sample_batch_id
        ),
        None,
    )
    assert test_batch is not None
    assert test_batch.sample_batch_name == "DB Test Batch"


@pytest.mark.asyncio
async def test_cascade_delete(session):
    """Test that deleting a workspace cascades to sample batches."""
    workspace = Workspace(
        workspace_id=gen_test_id(),
        workspace_name="Cascade Test Workspace",
        workspace_utc_created=datetime.now(timezone.utc),
    )
    session.add(workspace)
    await session.flush()

    sample_batch = SampleBatch(
        sample_batch_id=gen_test_id(),
        workspace_id=workspace.workspace_id,
        sample_batch_name="Cascade Test Batch",
        sample_batch_utc_created=datetime.now(timezone.utc),
    )
    session.add(sample_batch)
    await session.flush()

    batch_exists = await session.get(SampleBatch, sample_batch.sample_batch_id)
    assert batch_exists is not None

    await session.delete(workspace)
    await session.flush()

    result = await session.get(SampleBatch, sample_batch.sample_batch_id)
    assert result is None
