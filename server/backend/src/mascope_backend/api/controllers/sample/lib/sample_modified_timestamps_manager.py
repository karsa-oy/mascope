"""
Sample Modified Timestamps Manager

This module provides utilities for bulk updating sample-related modified timestamps.
All functions use bulk SQL operations to avoid triggering SQLAlchemy event listeners,
preventing circular timestamp updates.
"""

from datetime import datetime, timezone

from sqlalchemy import select, update

from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.db import SampleBatch, SampleItem, async_session
from mascope_backend.runtime import runtime


async def update_sample_items_modified_timestamp(sample_item_ids: list[str]) -> None:
    """
    Bulk update sample_item_utc_modified for specified sample items.

    :param sample_item_ids: List of sample item IDs to update
    """
    if not sample_item_ids:
        return

    async with async_session() as session:
        stmt = (
            update(SampleItem)
            .where(SampleItem.sample_item_id.in_(sample_item_ids))
            .values(sample_item_utc_modified=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()
    runtime.logger.debug(
        f"Updated modified timestamp for {len(sample_item_ids)} sample items"
    )


async def update_sample_batches_modified_timestamp(sample_batch_ids: list[str]) -> None:
    """
    Bulk update sample_batch_utc_modified for specified sample batches.

    :param sample_batch_ids: List of sample batch IDs to update
    """
    if not sample_batch_ids:
        return

    async with async_session() as session:
        stmt = (
            update(SampleBatch)
            .where(SampleBatch.sample_batch_id.in_(sample_batch_ids))
            .values(sample_batch_utc_modified=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()

    runtime.logger.debug(
        f"Updated modified timestamp for {len(sample_batch_ids)} sample batches"
    )


async def update_sample_modified_timestamps(
    sample_item_ids: list[str] | None = None,
    sample_batch_ids: list[str] | None = None,
) -> None:
    """
    Update both sample items and sample batches modified timestamps.

    Always updates _modified timestamps for both sample levels:
    - If sample_item_ids provided: updates those specific samples + their parent batches
    - If sample_batch_ids provided: updates ALL samples in those batches + the batches

    :param sample_item_ids: List of specific sample item IDs to update
    :param sample_batch_ids: List of sample batch IDs to update (includes all their samples)
    :raises ValueError: If both parameters are provided
    """
    if sample_item_ids and sample_batch_ids:
        raise ValueError("Provide either sample_item_ids OR sample_batch_ids, not both")

    if sample_item_ids:
        # Update specific sample items + their parent batches
        affected_sample_item_ids, affected_sample_batch_ids, *_ = (
            await fetch_affected_sample_data(sample_item_ids=sample_item_ids)
        )
    elif sample_batch_ids:
        # Update ALL sample items in the specified batches + the batches themselves
        async with async_session() as session:
            result = await session.execute(
                select(SampleItem.sample_item_id).where(
                    SampleItem.sample_batch_id.in_(sample_batch_ids)
                )
            )
            affected_sample_item_ids = [row for row in result.scalars().all()]
        affected_sample_batch_ids = sample_batch_ids
    else:
        return  # No parameters provided

    await update_sample_items_modified_timestamp(affected_sample_item_ids)
    await update_sample_batches_modified_timestamp(affected_sample_batch_ids)
