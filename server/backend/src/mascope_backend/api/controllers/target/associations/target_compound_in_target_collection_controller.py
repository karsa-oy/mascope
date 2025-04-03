from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    TargetCompoundInTargetCollection,
)
from mascope_backend.api.lib.api_features import api_controller


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
            "message": "Target compounds in target collection retrieved successfully.",
            "results": total,
            "data": [
                entry.to_dict() for entry in target_compound_in_target_collections
            ],
        }
