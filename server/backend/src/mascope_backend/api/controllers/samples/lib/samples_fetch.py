"""
Sample fetch helper

This module contains helper functions for fetching and processing
Sample View related data.
"""

from sqlalchemy import select
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


async def fetch_samples(sample_item_ids: list[str]) -> list[Sample]:
    """
    Retrieves samples by their IDs.

    - Execute a query to fetch the samples with the specified IDs.
    - Check if the samples exist. If any is missing, raise a NotFoundException.

    :param sample_item_ids: Unique identifiers of the samples to retrieve.
    :type sample_item_ids: list[str]
    :raises NotFoundException: If any of the samples with the given IDDs are not found.
    :return: The requested samples' SQLAlchemy models.
    :rtype: list[Sample]
    """
    async with async_session() as session:
        # -- Fetch samples by IDs --
        result = await session.execute(
            select(Sample).where(Sample.sample_item_id.in_(sample_item_ids))
        )
        samples = result.scalars().all()
        # -- Check if any of requested samples not found, raise exception --
        if len(samples) != len(sample_item_ids):
            missing_ids = set(sample_item_ids) - set(s.sample_item_id for s in samples)
            raise NotFoundException(f"Samples with IDs '{missing_ids}' not found")

    return samples
