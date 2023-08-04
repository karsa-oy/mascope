import asyncio
from sqlalchemy import asc, desc, func, and_
from sqlalchemy.future import select
from fastapi import HTTPException
from typing import List

from backend.db_api_rest import async_session
from backend.server import sio
from backend.api.match import match_batch_compute
from ..models.models import TargetCollectionInSampleBatch, SampleBatch, TargetCollection
from ..models.pydantic_models.target_collection_in_sample_batch_pydantic_model import (
    TargetCollectionInSampleBatchBase,
)


async def get_target_collections_in_sample_batch(
    sample_batch_id: str,
    target_collection_id: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
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
        count_stmt = select(func.count()).select_from(stmt)
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


async def create_target_collection_in_sample_batch(
    target_collections_in_sample_batch: List[TargetCollectionInSampleBatchBase],
    session=None,
):
    independent_transaction = False
    added_collections_to_sample_batch = []
    sample_batches_to_rematch = set()
    message_log = {}

    if session is None:
        independent_transaction = True
        session = async_session()

    for i, target_collection_in_sample_batch in enumerate(
        target_collections_in_sample_batch
    ):
        # Initialize messages list
        message_log[i] = {
            "status_code": 0,
            "messages": [],
        }

        # Check if target collection exists
        result = await session.execute(
            select(TargetCollection).filter(
                TargetCollection.target_collection_id
                == target_collection_in_sample_batch.target_collection_id
            )
        )
        target_collection = result.scalar_one_or_none()
        if not target_collection:
            message_log[i]["status_code"] = 404
            message_log[i]["messages"].append(
                "Target collection with target_collection_id: {} not found".format(
                    target_collection_in_sample_batch.target_collection_id
                )
            )
            continue

        # Check if sample batch exists
        result = await session.execute(
            select(SampleBatch).filter(
                SampleBatch.sample_batch_id
                == target_collection_in_sample_batch.sample_batch_id
            )
        )
        sample_batch = result.scalar_one_or_none()
        if not sample_batch:
            message_log[i]["status_code"] = 404
            message_log[i]["messages"].append(
                "Sample batch with sample_batch_id: {} not found".format(
                    target_collection_in_sample_batch.sample_batch_id
                )
            )
            continue

        # Check if the same entry already exists
        result = await session.execute(
            select(TargetCollectionInSampleBatch).filter(
                and_(
                    TargetCollectionInSampleBatch.target_collection_id
                    == target_collection_in_sample_batch.target_collection_id,
                    TargetCollectionInSampleBatch.sample_batch_id
                    == target_collection_in_sample_batch.sample_batch_id,
                )
            )
        )
        existing_entry = result.scalar_one_or_none()

        # If the entry already exists, log the error and skip this iteration
        if existing_entry:
            message_log[i]["status_code"] = 409
            message_log[i]["messages"].append(
                "The collection (target_collection_id: {} ) is already added to the sample batch (sample_batch_id: {} )".format(
                    target_collection_in_sample_batch.target_collection_id,
                    target_collection_in_sample_batch.sample_batch_id,
                )
            )
            continue

        # Create TargetCollectionInSampleBatch
        new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
            target_collection_id=target_collection_in_sample_batch.target_collection_id,
            sample_batch_id=target_collection_in_sample_batch.sample_batch_id,
        )
        session.add(new_target_collection_in_sample_batch)

        added_collections_to_sample_batch.append(new_target_collection_in_sample_batch)

        message_log[i]["status_code"] = 201
        message_log[i]["messages"].append(
            "The collection {} was successfully added to sample batch {}".format(
                target_collection_in_sample_batch.target_collection_id,
                target_collection_in_sample_batch.sample_batch_id,
            )
        )

        # Add the sample batch id to the set
        sample_batches_to_rematch.add(
            new_target_collection_in_sample_batch.sample_batch_id
        )

    if independent_transaction:
        await session.commit()
        # Run rematch for all sample batch ids in the set
        # FIX replace with request?
        for sample_batch_id in sample_batches_to_rematch:
            task = asyncio.create_task(
                match_batch_compute(
                    None,
                    sample_batch_id,
                )
            )
            await task
    else:
        await session.flush()

    return {
        "added_collections_to_sample_batch": added_collections_to_sample_batch,
        "message_logs": message_log,
    }


async def delete_target_collection_in_sample_batch(
    target_collection_id: str, sample_batch_id: str
):
    async with async_session() as session:
        # Check if target collection exists
        result = await session.execute(
            select(TargetCollection).filter(
                TargetCollection.target_collection_id == target_collection_id
            )
        )
        target_collection = result.scalar_one_or_none()
        if not target_collection:
            raise HTTPException(status_code=404, detail="Target collection not found")

        # Check if sample batch exists
        result = await session.execute(
            select(SampleBatch).filter(SampleBatch.sample_batch_id == sample_batch_id)
        )
        sample_batch = result.scalar_one_or_none()
        if not sample_batch:
            raise HTTPException(status_code=404, detail="Sample batch not found")

        # Check if the record exists
        result = await session.execute(
            select(TargetCollectionInSampleBatch).filter(
                and_(
                    TargetCollectionInSampleBatch.target_collection_id
                    == target_collection_id,
                    TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id,
                )
            )
        )
        target_collection_in_sample_batch = result.scalar_one_or_none()
        if not target_collection_in_sample_batch:
            raise HTTPException(
                status_code=404,
                detail="There is no such collection in the selected sample batch",
            )

        # Delete TargetCollectionInSampleBatch
        await session.delete(target_collection_in_sample_batch)
        await session.commit()

        # Reload affected sample batch
        await sio.emit(
            "sample_batch_reload",
            room=sample_batch_id,
            namespace="/",
        )
