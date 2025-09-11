"""
Sample batches fetch helper

This module contains helper functions for fetching and processing
sample batch-related data.
"""

from mascope_backend.db import async_session
from mascope_backend.db.models import SampleBatch
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException


async def fetch_sample_batch(sample_batch_id: str) -> SampleBatch:
    """
    Fetches the  SampleBatch object.

    :param sample_batch_id: ID of the sample batch to fetch.
    :type sample_batch_id: str
    :return: A SampleBatch object containing the sample batch data.
    :rtype: SampleBatch
    :raises NotFoundException: If the sample batch with the specified ID is not found.
    """
    async with async_session() as session:
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )
        return sample_batch
