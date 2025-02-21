"""
Fetch helper providing a consistent way to collect affected sample data for the current 
UI reload  notifications system.
"""

from typing import NamedTuple
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from mascope_server.db.models import SampleItem, SampleBatch
from mascope_server.db import async_session


class AffectedSampleData(NamedTuple):
    """
    Container for affected sample data used in reload events.

    All fields use the 'affected_' prefix for consistency.
    """

    affected_sample_item_ids: list[str]
    affected_sample_batch_ids: list[str]
    affected_sample_items: list[SampleItem] | None = None
    affected_sample_batches: list[SampleBatch] | None = None


async def fetch_affected_sample_data(
    filenames: list[str] | None = None,
    sample_item_ids: list[str] | None = None,
    include_objects: bool = False,
) -> AffectedSampleData:
    """
    Fetches affected sample data (item IDs, batch IDs, and related objects) based on
    filenames or sample item IDs.

    This function serves as a unified helper for collecting data needed for UI reload events.
    Exactly one of the parameters must be provided.

    :param filenames: List of filenames to fetch affected data for, defaults to None
    :type filenames: list[str], optional
    :param sample_item_ids: List of sample item IDs to fetch affected data for, defaults to None
    :type sample_item_ids: list[str], optional
    :param include_objects: Whether to include the actual SampleItem/SampleBatch objects
    :type include_objects: bool, defaults to False
    :return: Consolidated affected sample data including IDs and objects
    :rtype: AffectedSampleData
    :raises ValueError: If neither filenames nor sample_item_ids is provided,
                       or if both are provided
    """
    # Validate input parameters
    if (filenames is None and sample_item_ids is None) or (
        filenames is not None and sample_item_ids is not None
    ):
        raise ValueError(
            "Either filenames OR sample_item_ids must be provided, but not both"
        )

    async with async_session() as session:
        if include_objects:
            query = select(SampleItem).options(joinedload(SampleItem.sample_batch))
        else:
            query = select(SampleItem.sample_item_id, SampleItem.sample_batch_id)

        # Apply the appropriate filter
        if filenames:
            query = query.filter(SampleItem.filename.in_(filenames))
        else:
            query = query.filter(SampleItem.sample_item_id.in_(sample_item_ids))

        result = await session.execute(query)

        if include_objects:
            # Extract data from objects
            sample_items = result.scalars().all()

            # Collect data from objects
            affected_sample_item_ids = {item.sample_item_id for item in sample_items}
            affected_sample_batch_ids = {item.sample_batch_id for item in sample_items}
            affected_sample_batches = {item.sample_batch for item in sample_items}

            return AffectedSampleData(
                affected_sample_item_ids=list(affected_sample_item_ids),
                affected_sample_batch_ids=list(affected_sample_batch_ids),
                affected_sample_items=sample_items,
                affected_sample_batches=list(affected_sample_batches),
            )
        else:
            # Extract IDs only
            rows = result.all()

            affected_sample_item_ids = {row[0] for row in rows}
            affected_sample_batch_ids = {row[1] for row in rows}

            return AffectedSampleData(
                affected_sample_item_ids=list(affected_sample_item_ids),
                affected_sample_batch_ids=list(affected_sample_batch_ids),
            )
