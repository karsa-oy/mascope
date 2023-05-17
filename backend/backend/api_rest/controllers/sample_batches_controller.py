from sqlalchemy.future import select
from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from ..models.models import SampleBatch
from backend.db_api_rest import async_session


async def get_sample_batches(
    workspace_id: str, sort: str, order: str, page: int, limit: int
):
    async with async_session() as session:
        stmt = select(SampleBatch)

        if workspace_id:
            stmt = stmt.filter(SampleBatch.workspace_id == workspace_id)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleBatch, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleBatch, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_batches = result.scalars().all()

        return {
            "results": total,
            "data": [sample_batch.to_dict() for sample_batch in sample_batches],
        }


async def get_sample_batch_by_id(sample_batch_id: str):
    async with async_session() as session:
        stmt = select(SampleBatch).filter(
            SampleBatch.sample_batch_id == sample_batch_id
        )
        result = await session.execute(stmt)
        sample_batch = result.scalars().first()

        if not sample_batch:
            raise HTTPException(
                status_code=404,
                detail=f"SampleBatch with ID {sample_batch_id} not found",
            )

        return sample_batch.to_dict()
