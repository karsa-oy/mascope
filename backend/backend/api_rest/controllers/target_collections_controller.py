from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select

from backend.db_api_rest import async_session
from ..models.models import TargetCollection


async def get_target_collections(sort: str, order: str, page: int, limit: int):
    async with async_session() as session:
        stmt = select(TargetCollection)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCollection, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCollection, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_collections = result.scalars().all()

        return {
            "results": total,
            "data": [
                target_collection.to_dict() for target_collection in target_collections
            ],
        }


async def get_target_collection_by_id(target_collection_id: str):
    async with async_session() as session:
        stmt = select(TargetCollection).filter(
            TargetCollection.target_collection_id == target_collection_id
        )
        result = await session.execute(stmt)
        target_collection = result.scalars().first()

        if not target_collection:
            raise HTTPException(
                status_code=404,
                detail=f"TargetCollection with ID {target_collection_id} not found",
            )

        return target_collection.to_dict()
