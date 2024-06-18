from sqlalchemy import asc, desc, func
from sqlalchemy.future import select

from mascope_server.db import async_session
from ..utils.api_features import api_controller
from ..models.models import (
    TargetCompoundInTargetCollection,
)


@api_controller()
async def get_target_compound_in_target_collection(
    target_compound_id: str = None,
    target_collection_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100000,
):
    async with async_session() as session:
        stmt = select(TargetCompoundInTargetCollection)

        if target_compound_id:
            stmt = stmt.filter(
                TargetCompoundInTargetCollection.target_compound_id
                == target_compound_id
            )

        if target_collection_id:
            stmt = stmt.filter(
                TargetCompoundInTargetCollection.target_collection_id
                == target_collection_id
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(
                    desc(getattr(TargetCompoundInTargetCollection, sort))
                )
            else:
                stmt = stmt.order_by(
                    asc(getattr(TargetCompoundInTargetCollection, sort))
                )

        # Get total count
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt
        )
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_compound_in_target_collections = result.scalars().all()

        return {
            "results": total,
            "data": [
                entry.to_dict() for entry in target_compound_in_target_collections
            ],
        }
