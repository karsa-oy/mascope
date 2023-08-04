import asyncio
from backend.server import sio
from backend.api.match import match_batch_compute
from fastapi import HTTPException
from typing import List
from sqlalchemy import asc, desc, func, and_
from sqlalchemy.future import select

from backend.db_api_rest import async_session
from ..models.models import (
    TargetCompoundInTargetCollection,
    TargetCompound,
    TargetCollection,
    TargetCollectionInSampleBatch,
)
from ..models.pydantic_models.target_compound_in_target_collection_pydantic_model import (
    TargetCompoundInTargetCollectionBase,
)


async def get_target_compound_in_target_collection(
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


async def create_target_compound_in_target_collection(
    target_compounds_in_target_collection: List[TargetCompoundInTargetCollectionBase],
    session=None,
):
    independent_transaction = False
    added_compounds_to_target_collection = []
    sample_batches_to_rematch = set()
    message_log = {}

    if session is None:
        independent_transaction = True
        session = async_session()

    for i, target_compound_in_target_collection in enumerate(
        target_compounds_in_target_collection
    ):
        # Initialize messages list
        message_log[i] = {
            "status_code": 0,
            "messages": [],
        }

        # Check if target compound exists
        result = await session.execute(
            select(TargetCompound).filter(
                TargetCompound.target_compound_id
                == target_compound_in_target_collection.target_compound_id
            )
        )
        target_compound = result.scalar_one_or_none()
        if not target_compound:
            message_log[i]["status_code"] = 404
            message_log[i]["messages"].append(
                "Target compound with target_compound_id: {} not found".format(
                    target_compound_in_target_collection.target_compound_id
                )
            )
            continue

        # Check if target collection exists
        result = await session.execute(
            select(TargetCollection).filter(
                TargetCollection.target_collection_id
                == target_compound_in_target_collection.target_collection_id
            )
        )
        target_collection = result.scalar_one_or_none()
        if not target_collection:
            message_log[i]["status_code"] = 404
            message_log[i]["messages"].append(
                "Target collection with target_collection_id: {} not found".format(
                    target_compound_in_target_collection.target_collection_id
                )
            )
            continue

        # Check if the same entry already exists
        result = await session.execute(
            select(TargetCompoundInTargetCollection).filter(
                and_(
                    TargetCompoundInTargetCollection.target_collection_id
                    == target_compound_in_target_collection.target_collection_id,
                    TargetCompoundInTargetCollection.target_compound_id
                    == target_compound_in_target_collection.target_compound_id,
                )
            )
        )
        existing_entry = result.scalar_one_or_none()

        # If the entry already exists, log the error and skip this iteration
        if existing_entry:
            message_log[i]["status_code"] = 409
            message_log[i]["messages"].append(
                "The compound (target_compound_id: {} ) is already added to the target collection (target_collection_id: {} )".format(
                    target_compound_in_target_collection.target_compound_id,
                    target_compound_in_target_collection.target_collection_id,
                )
            )
            continue

        # Get the sample batches that contain the target collection
        result = await session.execute(
            select(TargetCollectionInSampleBatch).filter(
                TargetCollectionInSampleBatch.target_collection_id
                == target_compound_in_target_collection.target_collection_id
            )
        )
        affected_sample_batches = result.scalars().all()
        for batch in affected_sample_batches:
            sample_batches_to_rematch.add(batch.sample_batch_id)

        # Create TargetCompoundInTargetCollection
        new_target_compound_in_target_collection = TargetCompoundInTargetCollection(
            target_compound_id=target_compound_in_target_collection.target_compound_id,
            target_collection_id=target_compound_in_target_collection.target_collection_id,
        )
        session.add(new_target_compound_in_target_collection)
        added_compounds_to_target_collection.append(
            new_target_compound_in_target_collection
        )

        message_log[i]["status_code"] = 201
        message_log[i]["messages"].append(
            "The compound {} was successfully added to target collection {}".format(
                target_compound_in_target_collection.target_compound_id,
                target_compound_in_target_collection.target_collection_id,
            )
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
        "added_compounds_to_target_collection": added_compounds_to_target_collection,
        "message_logs": message_log,
    }


async def delete_target_compound_in_target_collection(
    target_compound_id: str, target_collection_id: str, session=None
):
    independent_transaction = False
    sample_batches_to_reload = set()

    if session is None:
        independent_transaction = True
        session = async_session()

    # Check if target compound exists
    result = await session.execute(
        select(TargetCompound).filter(
            TargetCompound.target_compound_id == target_compound_id
        )
    )
    target_compound = result.scalar_one_or_none()
    if not target_compound:
        raise HTTPException(status_code=404, detail="Target compound not found")

    # Check if target collection exists
    result = await session.execute(
        select(TargetCollection).filter(
            TargetCollection.target_collection_id == target_collection_id
        )
    )
    target_collection = result.scalar_one_or_none()
    if not target_collection:
        raise HTTPException(status_code=404, detail="Target collection not found")

    # Check if the record exists
    result = await session.execute(
        select(TargetCompoundInTargetCollection).filter(
            and_(
                TargetCompoundInTargetCollection.target_collection_id
                == target_collection_id,
                TargetCompoundInTargetCollection.target_compound_id
                == target_compound_id,
            )
        )
    )
    target_compound_in_target_collection = result.scalar_one_or_none()
    if not target_compound_in_target_collection:
        raise HTTPException(
            status_code=404,
            detail=f"Compound {target_compound_id} not found in the target collection {target_collection_id}",
        )

    # Get the sample batches that contain the target collection
    result = await session.execute(
        select(TargetCollectionInSampleBatch).filter(
            TargetCollectionInSampleBatch.target_collection_id == target_collection_id
        )
    )
    affected_sample_batches = result.scalars().all()
    for batch in affected_sample_batches:
        sample_batches_to_reload.add(batch.sample_batch_id)

    # Delete TargetCompoundInTargetCollection
    await session.delete(target_compound_in_target_collection)

    if independent_transaction:
        await session.commit()
        # Reload affected sample batches
        for sample_batch_id in sample_batches_to_reload:
            await sio.emit(
                "sample_batch_reload",
                room=sample_batch_id,
                namespace="/",
            )
    else:
        await session.flush()
