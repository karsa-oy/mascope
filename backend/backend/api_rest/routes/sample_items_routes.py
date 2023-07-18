from fastapi import APIRouter

from ..controllers.sample_items_controller import (
    get_sample_item_by_id,
    get_sample_items,
    create_sample_item,
    delete_sample_item,
    update_sample_item,
)
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
)

sample_items_router = APIRouter()


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


@sample_items_router.get("/api/sample_items/{sample_item_id}")
async def get_sample_item_by_id_route(sample_item_id: str):
    return await get_sample_item_by_id(sample_item_id)


@sample_items_router.post("/api/sample_items")
async def create_sample_item_route(sample_item: SampleItemCreate):
    return await create_sample_item(sample_item)


@sample_items_router.delete("/api/sample_items/{sample_item_id}")
async def delete_sample_item_route(sample_item_id: str):
    return await delete_sample_item(sample_item_id)


@sample_items_router.patch("/api/sample_items/{sample_item_id}")
async def update_sample_item_route(sample_item_id: str, sample_item: SampleItemUpdate):
    return await update_sample_item(sample_item_id, sample_item)
