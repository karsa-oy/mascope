from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ..controllers.sample_items_controller import (
    get_sample_items,
    get_sample_item,
    create_sample_item,
    delete_sample_item,
    update_sample_item,
    copy_sample_item,
)
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
    SampleItemCopy,
)
from ..models.exceptions import CustomException

sample_items_router = APIRouter()


@sample_items_router.get("/api/sample_items")
async def get_sample_items_route(
    sample_batch_id: str = Query(
        None,
        description="The sample batch ID for which you want to fetch the sample items.",
    ),
    filename: str = Query(
        None, description="The filename for which you want to fetch the sample items."
    ),
    sort: str = Query(
        None,
        description="The column name by which you want to sort the results. The column name should be one of the columns in the sample_Item table.",
    ),
    order: str = Query(
        None,
        description="Can either be asc for ascending order or desc for descending order.",
    ),
    page: int = Query(0, description="The page number for pagination, default 0"),
    limit: int = Query(10000, description="The number of results per page."),
):
    return await get_sample_items(
        sample_batch_id,
        filename,
        sort,
        order,
        page,
        limit,
    )


@sample_items_router.get("/api/sample_items/{sample_item_id}")
async def get_sample_item_route(sample_item_id: str):
    return await get_sample_item(sample_item_id)


@sample_items_router.post("/api/sample_items")
async def create_sample_item_route(
    sample_item: SampleItemCreate, skipReload: bool = False
):
    return await create_sample_item(sample_item, skipReload)


@sample_items_router.delete("/api/sample_items/{sample_item_id}")
async def delete_sample_item_route(sample_item_id: str):
    return await delete_sample_item(sample_item_id)


@sample_items_router.patch("/api/sample_items/{sample_item_id}")
async def update_sample_item_route(sample_item_id: str, sample_item: SampleItemUpdate):
    return await update_sample_item(sample_item_id, sample_item)


@sample_items_router.post("/api/sample_items/copy")
async def copy_sample_item_route(sample_item_copy: SampleItemCopy):
    try:
        return await copy_sample_item(sample_item_copy, True)
    except CustomException as e:
        return JSONResponse(
            status_code=400, content={"error": e.user_message, "detail": e.tech_message}
        )
