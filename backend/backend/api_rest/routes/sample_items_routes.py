from fastapi import APIRouter
from ..controllers.sample_items_controller import (
    get_sample_items,
    get_sample_item_by_id,
)

sample_items_router = APIRouter()


@sample_items_router.get("/api/sample_items/{sample_item_id}")
async def get_sample_item_by_id_route(sample_item_id: str):
    return await get_sample_item_by_id(sample_item_id)


@sample_items_router.get("/api/sample_items")
async def get_sample_items_route(
    sample_batch_id: str = None,
    filename: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
    include_tic: bool = False,
    include_intensity: bool = False,
    compounds: str = "",
):
    return await get_sample_items(
        sample_batch_id,
        filename,
        sort,
        order,
        page,
        limit,
        include_tic,
        include_intensity,
        compounds,
    )
