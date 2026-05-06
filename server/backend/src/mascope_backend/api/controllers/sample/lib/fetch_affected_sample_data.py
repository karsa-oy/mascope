"""
Fetch helper providing a consistent way to collect affected sample data for the current
UI reload  notifications system.
"""

from typing import NamedTuple

from sqlalchemy import select

from mascope_backend.db import Sample, SampleBatch, SampleItem, async_session


class AffectedSampleData(NamedTuple):
    """
    Container for affected sample data used in reload events.

    All fields use the 'affected_' prefix for consistency.
    """

    affected_sample_item_ids: list[str]
    affected_sample_batch_ids: list[str]
    affected_samples: list[Sample] = []
    affected_sample_batches: list[SampleBatch] = []


async def fetch_affected_sample_data(
    sample_item_ids: list[str] | None = None,
    sample_file_ids: list[str] | None = None,
    include_objects: bool = False,
) -> AffectedSampleData:
    """
    Fetch affected sample data for UI reload events.

    Unified helper for collecting sample IDs and optionally the full ORM
    objects needed to drive Socket.IO reload notifications.
    Exactly one filter parameter must be provided.

    Steps:
    - Validate exactly one filter param is given
    - Query SampleItem for matching item and batch IDs
    - If include_objects, fetch Sample view and SampleBatch ORM objects
    - Return AffectedSampleData with IDs and optional objects

    :param sample_item_ids: Sample item IDs to fetch affected data for.
    :type sample_item_ids: list[str] | None
    :param sample_file_ids: Sample file IDs to fetch affected data for.
    :type sample_file_ids: list[str] | None
    :param include_objects: Whether to include ORM objects in the result.
    :type include_objects: bool
    :raises ValueError: If zero or multiple filter parameters are provided.
    :return: Consolidated affected sample data.
    :rtype: AffectedSampleData
    """
    # --- Validate input - exactly one parameter must be provided ---
    provided_params = sum(x is not None for x in [sample_item_ids, sample_file_ids])
    if provided_params != 1:
        raise ValueError(
            "Provide either sample_item_ids or sample_file_ids, but not both."
        )

    async with async_session() as session:
        # --- Fetch affected item and batch IDs ---
        id_query = select(SampleItem.sample_item_id, SampleItem.sample_batch_id)

        if sample_item_ids:
            id_query = id_query.where(SampleItem.sample_item_id.in_(sample_item_ids))
        else:  # sample_file_ids
            id_query = id_query.where(SampleItem.sample_file_id.in_(sample_file_ids))

        id_result = await session.execute(id_query)
        rows = id_result.all()

        # Extract IDs
        affected_sample_item_ids = [row[0] for row in rows]
        affected_sample_batch_ids = list({row[1] for row in rows})

        # Early return if no IDs found or objects not requested
        if not affected_sample_item_ids or not include_objects:
            return AffectedSampleData(
                affected_sample_item_ids=affected_sample_item_ids,
                affected_sample_batch_ids=affected_sample_batch_ids,
            )

        # --- Fetch Sample view objects (includes filename and all joined data) ---
        sample_query = select(Sample).where(
            Sample.sample_item_id.in_(affected_sample_item_ids)
        )
        sample_result = await session.execute(sample_query)
        samples = sample_result.scalars().all()

        # --- Fetch SampleBatch objects ---
        batch_query = select(SampleBatch).where(
            SampleBatch.sample_batch_id.in_(affected_sample_batch_ids)
        )
        batch_result = await session.execute(batch_query)
        batches = batch_result.scalars().all()

        return AffectedSampleData(
            affected_sample_item_ids=affected_sample_item_ids,
            affected_sample_batch_ids=affected_sample_batch_ids,
            affected_samples=list(samples),
            affected_sample_batches=list(batches),
        )
