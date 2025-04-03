from typing import Optional, List, Tuple
from sqlalchemy import select
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    SampleItem,
    SampleBatch,
)

from mascope_backend.runtime import runtime


async def fetch_sample_item_ids(
    sample_item_id: Optional[str] = None, sample_batch_id: Optional[str] = None
) -> Tuple[List[str], str]:
    """
    Fetches sample item IDs and reference details based on provided sample_item_id or sample_batch_id.

    :param sample_item_id: Optional single sample item ID.
    :param sample_batch_id: Optional sample batch ID from which to derive sample item IDs.
    :return: A tuple containing a list of sample item IDs and a reference string for logging.
    :raises ValueError: If neither sample_item_id nor sample_batch_id is provided.
    """
    if not sample_item_id and not sample_batch_id:
        raise ValueError("Please provide either a sample item ID or a sample batch ID.")

    sample_item_ids = []
    sample_ref = ""
    async with async_session() as session:
        if sample_item_id:
            sample_item = await session.get(SampleItem, sample_item_id)
            if not sample_item:
                runtime.logger.warning(
                    f"No sample item found with ID '{sample_item_id}'"
                )
            sample_item_ids.append(sample_item_id)
            sample_ref = f"sample '{sample_item.sample_item_name}'"
        elif sample_batch_id:
            results = await session.execute(
                select(SampleItem).where(SampleItem.sample_batch_id == sample_batch_id)
            )
            sample_items = results.scalars().all()
            if not sample_items:
                runtime.logger.warning(
                    f"No sample items found for sample batch with ID '{sample_batch_id}'"
                )
            sample_item_ids = [item.sample_item_id for item in sample_items]
            batch = await session.get(SampleBatch, sample_batch_id)
            sample_ref = (
                f"sample batch '{batch.sample_batch_name}'"
                if batch
                else f"sample batch with ID '{sample_batch_id}'"
            )

    return sample_item_ids, sample_ref
