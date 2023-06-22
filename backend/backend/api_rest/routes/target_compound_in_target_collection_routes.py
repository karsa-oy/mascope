from fastapi import APIRouter
from ..controllers.target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collections,
)

target_compound_in_target_collection_router = APIRouter()


@target_compound_in_target_collection_router.get(
    "/api/target_compound_in_target_collections"
)
async def get_target_compound_in_target_collections_route(
    target_compound_id: str = None,
    target_collection_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_compound_in_target_collections(
        target_compound_id, target_collection_id, sort, order, page, limit
    )
