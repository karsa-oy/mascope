import asyncio

from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from datetime import datetime
from sqlalchemy.orm import joinedload


from backend.db_api_rest import async_session
from backend.server import sio
from backend.db.id import gen_id
from ..models.models import SampleBatch, TargetCollectionInSampleBatch
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchCreate,
    SampleBatchUpdate,
)
from backend.api.match import match_batch_compute


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


async def create_sample_batch(sample_batch: SampleBatchCreate):
    async with async_session() as session:
        new_sample_batch = SampleBatch(
            sample_batch_id=gen_id(16),
            workspace_id=sample_batch.workspace_id,
            sample_batch_name=sample_batch.sample_batch_name,
            sample_batch_description=sample_batch.sample_batch_description,
            build_params=sample_batch.build_params,
            filter_params=sample_batch.filter_params,
            sample_batch_utc_created=datetime.utcnow(),
        )
        session.add(new_sample_batch)
        await session.commit()
        await session.refresh(new_sample_batch)

        # associations to target collections
        for target_collection_id in sample_batch.target_collection_id:
            new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                target_collection_id=target_collection_id,
                sample_batch_id=new_sample_batch.sample_batch_id,
            )
            session.add(new_target_collection_in_sample_batch)
        await session.commit()

        # emit the event to inform the clients about the new workspace
        await sio.emit(
            "workspace_reload", room=sample_batch.workspace_id, namespace="/"
        )

        return new_sample_batch


async def delete_sample_batch(sample_batch_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(SampleBatch).filter(SampleBatch.sample_batch_id == sample_batch_id)
        )
        sample_batch = result.scalar_one_or_none()
        if not sample_batch:
            raise HTTPException(status_code=404, detail="Sample batch not found")

        await session.delete(sample_batch)
        await session.commit()
        await sio.emit(
            "workspace_reload", room=sample_batch.workspace_id, namespace="/"
        )


async def update_sample_batch(sample_batch_id: str, sample_batch: SampleBatchUpdate):
    async with async_session() as session:
        stmt = (
            select(SampleBatch)
            .options(joinedload(SampleBatch.target_collection))
            .where(SampleBatch.sample_batch_id == sample_batch_id)
        )
        result = await session.execute(stmt)
        existing_sample_batch = result.scalars().first()
        if not existing_sample_batch:
            raise HTTPException(status_code=404, detail="Sample batch not found")

        # Determine whether a rematch is needed
        rematch = False
        if set(sample_batch.build_params["ion_mechanisms"]) != set(
            existing_sample_batch.build_params["ion_mechanisms"]
        ):
            rematch = True
        if set(sample_batch.target_collection_id) != {
            item.target_collection_id
            for item in existing_sample_batch.target_collection
        }:
            rematch = True

        # Update the existing sample batch
        update_data = sample_batch.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key in ["build_params", "filter_params"]:
                # Skip build_params and filter_params for now as they are done below
                continue
            setattr(existing_sample_batch, key, value)
        existing_sample_batch.sample_batch_utc_modified = datetime.utcnow()

        # Update the build_params and filter_params with the stringified versions
        existing_sample_batch.build_params = sample_batch.build_params
        existing_sample_batch.filter_params = sample_batch.filter_params

        # Update target collections associations
        if "target_collection_id" in update_data:
            # Remove all previous associations
            existing_sample_batch.target_collection.clear()
            # Add new associations
            for target_collection_id in sample_batch.target_collection_id:
                new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                    target_collection_id=target_collection_id,
                    sample_batch_id=existing_sample_batch.sample_batch_id,
                )
                session.add(new_target_collection_in_sample_batch)

        await session.commit()
        # Inform clients about the update
        if rematch:
            # FIX replace with request
            task = sio.start_background_task(
                match_batch_compute, None, existing_sample_batch.sample_batch_id
            )
            await asyncio.gather(task)
        await sio.emit(
            "workspace_reload",
            room=existing_sample_batch.workspace_id,
            namespace="/",
        )

        return existing_sample_batch
