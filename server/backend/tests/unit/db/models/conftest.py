"""
Fixtures for database model tests.
"""

from datetime import datetime, timezone

import pytest_asyncio
from test_utils import gen_test_id

from mascope_backend.db import SampleBatch, Dataset


@pytest_asyncio.fixture
async def db_test_dataset(session):
    """Create a dataset for database testing."""
    dataset = Dataset(
        dataset_id=gen_test_id(),
        dataset_name="DB Test Dataset",
        dataset_description="A dataset for DB testing",
        dataset_utc_created=datetime.now(timezone.utc),
    )
    session.add(dataset)
    await session.flush()
    yield dataset


@pytest_asyncio.fixture
async def db_test_sample_batch(session, db_test_dataset):
    """Create a sample batch linked to `db_test_dataset`."""
    batch = SampleBatch(
        sample_batch_id=gen_test_id(),
        dataset_id=db_test_dataset.dataset_id,
        sample_batch_name="DB Test Batch",
        sample_batch_description="A batch for DB testing",
        sample_batch_utc_created=datetime.now(timezone.utc),
    )
    session.add(batch)
    await session.flush()
    yield batch
