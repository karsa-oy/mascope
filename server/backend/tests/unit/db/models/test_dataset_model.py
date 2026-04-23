"""
Unit tests for the Dataset SQLAlchemy model.
Tests model creation, validation, and relationships.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from test_utils import gen_test_id

from mascope_backend.db import SampleBatch, Dataset


@pytest.mark.asyncio
async def test_create_dataset(session):
    """Test creating a dataset with valid data."""
    dataset = Dataset(
        dataset_id=gen_test_id(),
        dataset_name="Create Test Dataset",
        dataset_description="Testing dataset creation",
        dataset_utc_created=datetime.now(timezone.utc),
    )
    session.add(dataset)
    await session.flush()

    result = await session.get(Dataset, dataset.dataset_id)

    assert result is not None
    assert result.dataset_id == dataset.dataset_id
    assert result.dataset_name == "Create Test Dataset"
    assert result.dataset_description == "Testing dataset creation"
    assert result.dataset_utc_created is not None


@pytest.mark.asyncio
async def test_dataset_name_required(session):
    """Test that dataset_name is required."""
    dataset = Dataset(
        dataset_id=gen_test_id(),
        dataset_description="A test dataset without name",
    )
    session.add(dataset)
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_dataset_relationship(session, db_test_dataset, db_test_sample_batch):
    """Test dataset relationship with sample batches."""
    assert db_test_sample_batch.dataset_id == db_test_dataset.dataset_id

    stmt = select(SampleBatch).where(
        SampleBatch.dataset_id == db_test_dataset.dataset_id
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
    """Test that deleting a dataset cascades to sample batches."""
    dataset = Dataset(
        dataset_id=gen_test_id(),
        dataset_name="Cascade Test Dataset",
        dataset_utc_created=datetime.now(timezone.utc),
    )
    session.add(dataset)
    await session.flush()

    sample_batch = SampleBatch(
        sample_batch_id=gen_test_id(),
        dataset_id=dataset.dataset_id,
        sample_batch_name="Cascade Test Batch",
        sample_batch_utc_created=datetime.now(timezone.utc),
    )
    session.add(sample_batch)
    await session.flush()

    batch_exists = await session.get(SampleBatch, sample_batch.sample_batch_id)
    assert batch_exists is not None

    await session.delete(dataset)
    await session.flush()

    result = await session.get(SampleBatch, sample_batch.sample_batch_id)
    assert result is None
