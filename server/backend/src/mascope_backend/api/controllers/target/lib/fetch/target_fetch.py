from typing import Tuple
from sqlalchemy import select
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)


async def fetch_compound_collections_and_batches(
    target_compound_id: str,
) -> Tuple[str, str]:
    """
    Retrieves the associated target collection IDs and sample batch IDs for a given target compound ID.

    This function is used to fetch the collections that a target compound belongs to and the sample batches
    associated with those collections.

    :param target_compound_id: The ID of the target compound.
    :type target_compound_id: str
    :return: A tuple containing two sets - sample_batches_ids and target_collections_ids.
    :rtype: tuple(set, set)
    """
    async with async_session() as session:
        # Get the target collections for this compound
        target_collections = await session.execute(
            select(TargetCompoundInTargetCollection.target_collection_id).where(
                TargetCompoundInTargetCollection.target_compound_id
                == target_compound_id
            )
        )
        target_collections_ids = {tc[0] for tc in target_collections}

        # Get all affected sample batches
        sample_batches = await session.execute(
            select(TargetCollectionInSampleBatch.sample_batch_id).where(
                TargetCollectionInSampleBatch.target_collection_id.in_(
                    target_collections_ids
                )
            )
        )
        sample_batches_ids = {sb[0] for sb in sample_batches}

        return sample_batches_ids, target_collections_ids
