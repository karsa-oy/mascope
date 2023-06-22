from fastapi import APIRouter
from ..controllers.target_collection_in_sample_batch_controller import (
    get_target_collections_in_sample_batch,
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
