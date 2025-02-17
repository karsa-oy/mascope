"""
Sample batches fetch helper

This module contains helper functions for fetching and processing
sample batch-related data.
"""

from mascope_server.db import async_session
from mascope_server.db.models import SampleBatch, SampleItem
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from sqlalchemy import distinct, select


class SampleBatchData:
    """
    A data container to allow dot notation access to sample batch data.
    """

    def __init__(self, sample_batch, ion_mechanisms):
        self.__dict__.update(sample_batch.__dict__)
        self.ion_mechanisms = ion_mechanisms


async def fetch_sample_batch_data(sample_batch_id: str) -> SampleBatchData:
    """
    Fetches the sample batch and retrieves the associated ionization mechanisms, returning a SampleBatchData object.

    :param sample_batch_id: ID of the sample batch to fetch.
    :type sample_batch_id: str
    :return: A SampleBatchData object containing the sample batch data and ion mechanisms.
    :rtype: SampleBatchData
    :raises NotFoundException: If the sample batch with the specified ID is not found.
    """
    async with async_session() as session:
        # Fetch the sample batch
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Retrieve the ion mechanisms from build_params
        build_params = sample_batch.build_params
        ion_mechanisms = build_params.get("ion_mechanisms", [])

        # Return the SampleBatchData object with unpacked data
        return SampleBatchData(sample_batch, ion_mechanisms)


async def fetch_sample_batch_ids(
    filenames: list[str] = None, sample_item_ids: list[str] = None
) -> list[str]:
    """
    Fetches unique sample batch IDs for the given filenames and/or
    sample item IDs.

    :param filenames: List of filenames to fetch sample batche ids for
    :type filenames: list[str], optional
    :param sample_item_ids: List of sample_item_ids to fetch sample batch ids for
    :type sample_item_ids: list[str], optional
    :return: List of unique sample batch IDs
    :rtype: list[str]
    """
    async with async_session() as session:
        if filenames:
            query = select(SampleItem.sample_batch_id).where(
                SampleItem.filename.in_(filenames)
            )
        elif sample_item_ids:
            query = select(SampleItem.sample_batch_id).where(
                SampleItem.sample_item_id.in_(sample_item_ids)
            )
        batch_ids = await session.scalars(query)
        return list(set(batch_ids))
