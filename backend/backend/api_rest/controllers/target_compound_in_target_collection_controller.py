from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select

from backend.db_api_rest import async_session
from ..models.models import TargetCompoundInTargetCollection


async def get_target_compound_in_target_collections(
    target_compound_id: str,
    target_collection_id: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
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
        count_stmt = select(func.count()).select_from(stmt)
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
