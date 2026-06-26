"""
Tests: target collection ↔ sample batch type compatibility.

Verifies the type-compatibility rules enforced by
``validate_sample_batches_for_collection`` when assigning batches to a
collection via ``PATCH /api/target/collections/{id}``.

Key behaviour under test:
- TARGETS collections may now be assigned to ACQUISITION batches (new) as well
  as ANALYSIS batches.
- CALIBRANTS collections remain restricted to ANALYSIS batches, proving the
  validation is still enforced (negative control).
"""

import pytest
import pytest_asyncio

from mascope_backend.db import SampleBatch, TargetCollection
from mascope_backend.db.id import gen_id


_BATCH_NAME = "Acquisition Batch (type-compat)"


@pytest_asyncio.fixture
async def acquisition_batch(async_session_factory, alpha_dataset):
    """An ACQUISITION-type sample batch inside the Alpha dataset."""
    batch_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            SampleBatch(
                sample_batch_id=batch_id,
                dataset_id=alpha_dataset,
                sample_batch_name=_BATCH_NAME,
                sample_batch_type="ACQUISITION",
            )
        )
        await session.commit()
    return batch_id


@pytest_asyncio.fixture
async def targets_collection(async_session_factory, ws_alpha):
    """A TARGETS collection scoped to workspace Alpha."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Targets (type-compat)",
                target_collection_type="TARGETS",
                workspace_id=ws_alpha["workspace_id"],
            )
        )
        await session.commit()
    return tc_id


@pytest_asyncio.fixture
async def calibrants_collection(async_session_factory, ws_alpha):
    """A CALIBRANTS collection scoped to workspace Alpha."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Calibrants (type-compat)",
                target_collection_type="CALIBRANTS",
                workspace_id=ws_alpha["workspace_id"],
            )
        )
        await session.commit()
    return tc_id


@pytest.mark.asyncio
async def test_targets_collection_can_be_assigned_to_acquisition_batch(
    editor_client, targets_collection, acquisition_batch
):
    """TARGETS collections may now be assigned to ACQUISITION batches."""
    resp = await editor_client.patch(
        f"/api/target/collections/{targets_collection}",
        json={
            "target_collection_name": "Targets (type-compat)",
            "target_collection_type": "TARGETS",
            "sample_batch_ids": [acquisition_batch],
        },
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_targets_collection_still_allowed_on_analysis_batch(
    editor_client, targets_collection, alpha_batch
):
    """TARGETS on ANALYSIS batches keeps working (regression)."""
    resp = await editor_client.patch(
        f"/api/target/collections/{targets_collection}",
        json={
            "target_collection_name": "Targets (type-compat)",
            "target_collection_type": "TARGETS",
            "sample_batch_ids": [alpha_batch],
        },
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_calibrants_collection_rejected_on_acquisition_batch(
    editor_client, calibrants_collection, acquisition_batch
):
    """CALIBRANTS collections are still restricted to ANALYSIS batches."""
    resp = await editor_client.patch(
        f"/api/target/collections/{calibrants_collection}",
        json={
            "target_collection_name": "Calibrants (type-compat)",
            "target_collection_type": "CALIBRANTS",
            "sample_batch_ids": [acquisition_batch],
        },
    )
    assert resp.status_code == 400
