"""
Target collection validation helpers.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)
from mascope_backend.db import SampleBatch, TargetCollection, async_session
from mascope_backend.runtime import runtime


async def fetch_target_collection(target_collection_id: str) -> TargetCollection:
    """
    Retrieves a target collection from the database by its ID, including its associated sample batches
    and target compounds.

    :param target_collection_id: The ID of the target collection to fetch.
    :type target_collection_id: str
    :return: The target collection with its associated sample batches and target compounds.
    :rtype: TargetCollection
    :raises NotFoundException: If the target collection with the specified ID is not found.
    """
    async with async_session() as session:
        if not (
            collection := await session.get(
                TargetCollection,
                target_collection_id,
                options=[
                    joinedload(TargetCollection.sample_batch),
                    joinedload(TargetCollection.target_compound),
                ],
            )
        ):
            raise NotFoundException(
                f"Target collection with ID '{target_collection_id}' not found"
            )

    return collection


async def validate_sample_batches_for_collection(
    sample_batch_ids: list | None, target_collection_type: str
) -> None:
    """
    Validates that sample batches can be assigned to a target collection type.

    :param sample_batch_ids: List of sample batch IDs to validate
    :param target_collection_type: Type of the target collection
    :raises ValueError: If any batch type is not allowed for the collection type
    """
    if not sample_batch_ids:
        return
    # Get allowed batch types for this collection type
    allowed_batch_types = target_collection_config.get_allowed_batch_types(
        target_collection_type
    )

    async with async_session() as session:
        stmt = select(func.count()).where(
            SampleBatch.sample_batch_id.in_(sample_batch_ids),
            SampleBatch.sample_batch_type.not_in(allowed_batch_types),
        )
        invalid_count = await session.scalar(stmt)

        if invalid_count > 0:
            message = (
                f"{target_collection_type} collections can only be assigned to {', '.join(allowed_batch_types)} batches. "
                f"Found {invalid_count} invalid batch(es)"
            )
            runtime.logger.warning(message)
            raise ValueError(message)


async def validate_collections_for_batch(
    target_collection_ids: list | None, sample_batch_type: str
) -> None:
    """
    Validates that target collections can be assigned to a sample batch type.

    :param target_collection_ids: List of target collection IDs to validate
    :param sample_batch_type: Type of the sample batch
    :raises ValueError: If any collection type is not allowed for the batch type
    """
    if not target_collection_ids:
        return
    # Get allowed collection types for this batch type
    allowed_collection_types = sample_batch_config.get_allowed_collection_types(
        sample_batch_type
    )

    async with async_session() as session:
        stmt = select(func.count()).where(
            TargetCollection.target_collection_id.in_(target_collection_ids),
            TargetCollection.target_collection_type.not_in(allowed_collection_types),
        )
        invalid_count = await session.scalar(stmt)

        if invalid_count > 0:
            message = (
                f"{sample_batch_type} batches can only use {', '.join(allowed_collection_types)} collections. "
                f"Found {invalid_count} invalid collection(s)"
            )
            runtime.logger.warning(message)
            raise ValueError(message)
