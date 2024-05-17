from sqlalchemy import select
from backend.db import async_session
from backend.api_sio import sio
from ..models.models import (
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)


async def get_affected_batches_and_collections(target_compound_id: str):
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
