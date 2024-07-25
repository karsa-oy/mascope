from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)

from mascope_server.db import async_session
from ..utils.api_features import api_controller
from ..models.models import TargetCollectionInSampleBatch


@api_controller()
async def get_target_collections_in_sample_batch(
    sample_batch_id: str = None,
    target_collection_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100000,
):
    async with async_session() as session:
        stmt = select(TargetCollectionInSampleBatch)

        if sample_batch_id:
            stmt = stmt.filter(
                TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id
            )

        if target_collection_id:
            stmt = stmt.filter(
                TargetCollectionInSampleBatch.target_collection_id
                == target_collection_id
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCollectionInSampleBatch, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCollectionInSampleBatch, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt
        )
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_collections_in_sample_batch = result.scalars().all()

        return {
            "results": total,
            "data": [
                target_collection_in_sample_batch.to_dict()
                for target_collection_in_sample_batch in target_collections_in_sample_batch
            ],
        }
