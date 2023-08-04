from typing import List
from fastapi import APIRouter
from ..controllers.target_collection_in_sample_batch_controller import (
    get_target_collections_in_sample_batch,
    create_target_collection_in_sample_batch,
    delete_target_collection_in_sample_batch,
)
from ..models.pydantic_models.target_collection_in_sample_batch_pydantic_model import (
    TargetCollectionInSampleBatchBase,
)

target_collection_in_sample_batch_router = APIRouter()


@target_collection_in_sample_batch_router.get("/api/target_collections_in_sample_batch")
async def get_target_collections_in_sample_batch_route(
    sample_batch_id: str = None,
    target_collection_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_collections_in_sample_batch(
        sample_batch_id, target_collection_id, sort, order, page, limit
    )


@target_collection_in_sample_batch_router.post(
    "/api/target_collections_in_sample_batch"
)
async def create_target_collection_in_sample_batch_route(
    target_collections_in_sample_batch: List[TargetCollectionInSampleBatchBase],
):
    result = await create_target_collection_in_sample_batch(
        target_collections_in_sample_batch
    )
    response = {
        "added_collections_to_sample_batch_count": len(
            result["added_collections_to_sample_batch"]
        ),
        "added_collections_to_sample_batch": result[
            "added_collections_to_sample_batch"
        ],
        "message-logs": result["message_logs"],
    }
    return response


@target_collection_in_sample_batch_router.delete(
    "/api/target_collections_in_sample_batch/{target_collection_id}/{sample_batch_id}"
)
async def delete_target_collection_in_sample_batch_route(
    target_collection_id: str, sample_batch_id: str
):
    return await delete_target_collection_in_sample_batch(
        target_collection_id, sample_batch_id
    )
