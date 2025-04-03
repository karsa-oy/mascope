"""
Sample fetch helper

This module contains helper functions for fetching and processing
Sample View related data.
"""

from mascope_backend.db import async_session
from mascope_backend.db.models import Sample
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException


async def fetch_sample(sample_item_id: str) -> Sample:
    """
    Retrieves a single sample by its ID.

    Steps:
    1. Execute a query to fetch the sample with the specified ID.
    2. Check if the sample exists. If not, raise a NotFoundException.
    3. Return the sample's SQLAlchemy model.

    :param sample_item_id: Unique identifier of the sample to retrieve.
    :type sample_item_id: str
    :raises NotFoundException: If the sample with the given ID is not found.
    :return: The requested sample's SQLAlchemy model.
    :rtype: Sample
    """
    async with async_session() as session:
        # Step 1: Fetch sample by ID
        sample = await session.get(Sample, sample_item_id)

        # Step 2: If sample not found, raise exception
        if not sample:
            raise NotFoundException(f"Sample with ID '{sample_item_id}' not found")
    # Step 3: Return sample
    return sample
