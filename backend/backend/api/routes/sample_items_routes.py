from fastapi import APIRouter, BackgroundTasks, Depends, Request
from ..utils.api_features import api_route

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
    GetSampleItemsQueryParams,
    SampleItemCopyBody,
)

sample_items_router = APIRouter()


@sample_items_router.get("/api/sample_items")
@api_route()
async def get_sample_items_route(
    query_params: GetSampleItemsQueryParams = Depends(),
):
    return await get_sample_items(**query_params.dict())


@sample_items_router.get("/api/sample_items/{sample_item_id}")
@api_route()
async def get_sample_item_route(sample_item_id: str):
    return await get_sample_item(sample_item_id)


@sample_items_router.post("/api/sample_items")
@api_route(
    status_code_success=201,
    include_message=True,
    success_message="Sample item created successfully",
)
async def create_sample_item_route(sample_item: SampleItemCreate):
    return await create_sample_item(
        sample_item=sample_item, independent_transaction=True
    )


@sample_items_router.patch("/api/sample_items/{sample_item_id}")
@api_route(include_message=True, success_message="Sample item updated successfully")
async def update_sample_item_route(sample_item_id: str, sample_item: SampleItemUpdate):
    return await update_sample_item(sample_item_id, sample_item)


@sample_items_router.delete("/api/sample_items/{sample_item_id}")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Sample item deleted successfully",
)
async def delete_sample_item_route(sample_item_id: str):
    return await delete_sample_item(sample_item_id)


@sample_items_router.post("/api/sample_items/{sample_item_id}/copy")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Coping sample item has started",
)
async def copy_sample_item_route(
    request: Request,
    sample_item_id: str,
    body: SampleItemCopyBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(
        copy_sample_item,
        sample_item_id=sample_item_id,
        sample_batch_id=body.sample_batch_id,
        sample_item_name=body.sample_item_name,
        independent_transaction=True,
        background_tasks=background_tasks,
        sid=sid,
    )
