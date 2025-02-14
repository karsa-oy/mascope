from typing import Optional, List, Tuple, NamedTuple
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from mascope_server.db import async_session
from mascope_server.db.models import (
    SampleItem,
    SampleBatch,
)
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException

from mascope_server.runtime import runtime


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


async def fetch_sample_item_ids_for_filenames(filenames: list[str]) -> list[str]:
    """
    Fetches unique sample item IDs for the given filenames.

    :param filenames: List of filenames to fetch sample batches for
    :type filenames: list[str]
    :return: List of unique sample item IDs
    :rtype: list[str]
    """
    async with async_session() as session:
        query = select(SampleItem.sample_item_id).where(
            SampleItem.filename.in_(filenames)
        )
        item_ids = await session.scalars(query)
        return list(set(item_ids))


class AffectedSampleData(NamedTuple):
    sample_item_ids: List[str]
    sample_batch_ids: List[str]
    sample_items: List[SampleItem]
    sample_batches: List[SampleBatch]


async def fetch_affected_sample_data_for_filename(
    filename: str,
) -> AffectedSampleData:
    """
    Fetches affected sample item IDs and their corresponding batch IDs for a given filename.

    :param filename: Filename to fetch affected samples for
    :type filename: str
    :return: AffectedSampleData containing sample IDs and objects
    :rtype: AffectedSampleData
    :raises NotFoundException: If no sample items found for the given filename
    """
    async with async_session() as session:
        result = await session.execute(
            select(SampleItem)
            .options(joinedload(SampleItem.sample_batch))
            .filter(SampleItem.filename == filename)
        )
        sample_items = result.scalars().all()

        if not sample_items:
            raise NotFoundException(
                f"No sample items found for sample file '{filename}'"
            )

        return AffectedSampleData(
            sample_item_ids=[item.to_dict()["sample_item_id"] for item in sample_items],
            sample_batch_ids=list(
                {item.to_dict()["sample_batch_id"] for item in sample_items}
            ),
            sample_items=sample_items,
            sample_batches=list({item.sample_batch for item in sample_items}),
        )
