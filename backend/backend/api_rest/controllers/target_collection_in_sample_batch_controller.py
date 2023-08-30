import asyncio
from sqlalchemy import asc, desc, func, and_
from sqlalchemy.future import select
from typing import List

from backend.db_api_rest import async_session
from backend.server import sio
from ..controllers.sample_batches_controller import (
    compute_sample_batch_matches,
)
from ..models.models import TargetCollectionInSampleBatch, SampleBatch, TargetCollection
from ..models.pydantic_models.target_collection_in_sample_batch_pydantic_model import (
    TargetCollectionInSampleBatchBase,
)
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchComputeMatch,
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
    skipRematch: bool = False,
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
        await sio.emit(
            "targets_all_reload",
            namespace="/",
        )
        # TODO_match
        if not skipRematch and sample_batches_to_rematch:
            sample_batches = [
                SampleBatchComputeMatch(sample_batch_id=sample_batch_id)
                for sample_batch_id in sample_batches_to_rematch
            ]
            await compute_sample_batch_matches(sample_batches)
        elif skipRematch:
            # Reload the sample batches if compute_sample_batch_matches is skipped
            for sample_batch_id in sample_batches_to_rematch:
                await sio.emit(
                    "sample_batch_reload",
                    room=sample_batch_id,
                    namespace="/",
                )

    else:
        await session.flush()

    return {
        "added_collections_to_sample_batch": added_collections_to_sample_batch,
        "message_logs": message_log,
    }


async def delete_target_collections_in_sample_batch(
    target_collections_in_sample_batch: List[TargetCollectionInSampleBatchBase],
    skipRematch: bool = False,
):
    message_log = {}
    sample_batches_to_rematch = set()

    session = async_session()

    for i, item in enumerate(target_collections_in_sample_batch):
        # Initialize messages list
        message_log[i] = {
            "status_code": 0,
            "messages": [],
        }

        # Check if target collection exists
        result = await session.execute(
            select(TargetCollection).filter(
                TargetCollection.target_collection_id == item.target_collection_id
            )
        )
        target_collection = result.scalar_one_or_none()

        if not target_collection:
            message_log[i]["status_code"] = 404
            message_log[i]["messages"].append("Target collection not found")
            continue

        # Check if sample batch exists
        result = await session.execute(
            select(SampleBatch).filter(
                SampleBatch.sample_batch_id == item.sample_batch_id
            )
        )
        sample_batch = result.scalar_one_or_none()

        if not sample_batch:
            message_log[i]["status_code"] = 404
            message_log[i]["messages"].append("Sample batch not found")
            continue

        # Check if the record exists
        result = await session.execute(
            select(TargetCollectionInSampleBatch).filter(
                and_(
                    TargetCollectionInSampleBatch.target_collection_id
                    == item.target_collection_id,
                    TargetCollectionInSampleBatch.sample_batch_id
                    == item.sample_batch_id,
                )
            )
        )
        target_collection_in_sample_batch = result.scalar_one_or_none()

        if not target_collection_in_sample_batch:
            message_log[i]["status_code"] = 404
            message_log[i]["messages"].append(
                "There is no such collection in the selected sample batch"
            )
            continue

        message_log[i]["status_code"] = 200
        message_log[i]["messages"].append(
            f"Target collection (id: {item.target_collection_id}) was removed from the sample batch (id: {item.sample_batch_id})"
        )
        # Add the sample batch id to the set
        sample_batches_to_rematch.add(item.sample_batch_id)
        # Delete TargetCollectionInSampleBatch
        await session.delete(target_collection_in_sample_batch)

    await session.commit()

    # TODO_match
    if not skipRematch and sample_batches_to_rematch:
        sample_batches = [
            SampleBatchComputeMatch(sample_batch_id=id)
            for id in sample_batches_to_rematch
        ]
        await compute_sample_batch_matches(sample_batches)
    elif skipRematch:
        # Reload the sample batches if compute_sample_batch_matches is skipped
        for sample_batch_id in sample_batches_to_rematch:
            await sio.emit(
                "sample_batch_reload",
                room=sample_batch_id,
                namespace="/",
            )

    await sio.emit(
        "targets_all_reload",
        namespace="/",
    )

    return {"message_logs": message_log}
