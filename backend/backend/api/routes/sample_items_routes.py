from fastapi import APIRouter, BackgroundTasks, Depends, Request
from backend.db.id import gen_id
from ..utils.api_features import api_route
from ..exceptions import NotFoundException

from ..controllers.sample_items_controller import (
    get_sample_items,
    get_sample_item,
    create_sample_item,
    delete_sample_item,
    update_sample_item,
    copy_sample_item,
    process_sample_item,
)
from ..controllers.sample_files_controller import get_sample_files
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
    GetSampleItemsQueryParams,
    SampleItemCopyBody,
    SampleItemProcessBody,
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
    status_code=201,
    include_message=True,
    success_message="Sample item created successfully",
)
async def create_sample_item_route(sample_item: SampleItemCreate):
    return await create_sample_item(
        sample_item=sample_item, independent_transaction=True
    )


@sample_items_router.patch("/api/sample_items/{sample_item_id}")
@api_route()
async def update_sample_item_route(sample_item_id: str, sample_item: SampleItemUpdate):
    return await update_sample_item(sample_item_id, sample_item)


@sample_items_router.delete("/api/sample_items/{sample_item_id}")
@api_route()
async def delete_sample_item_route(sample_item_id: str):
    return await delete_sample_item(sample_item_id)


@sample_items_router.post("/api/sample_items/{sample_item_id}/copy")
@api_route(
    status_code=202,
)
async def copy_sample_item_route(
    request: Request,
    sample_item_id: str,
    body: SampleItemCopyBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)
    background_tasks.add_task(
        copy_sample_item,
        sample_item_id=sample_item_id,
        sample_batch_id=body.sample_batch_id,
        sample_item_name=body.sample_item_name,
        independent_transaction=True,
        background_tasks=background_tasks,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Copying sample '{body.sample_item_name}', please wait.",
        "process_id": process_id,
    }


@sample_items_router.post("/api/sample_items/process")
@api_route(
    status_code=202,
)
async def process_sample_item_route(
    request: Request, body: SampleItemProcessBody, background_tasks: BackgroundTasks
):
    # Verify the existance of sample file
    sample_file_data = await get_sample_files(filename=body.sample_item.filename)
    if not sample_file_data["data"][0]:
        raise NotFoundException(f"Sample file '{body.sample_item.filename}' not found")

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        process_sample_item,
        sample_item=body.sample_item,
        mz_calibration_params=body.mz_calibration_params,
        alarms_list=body.alarms_list,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )

    return {
        "message": f"Processing sample '{body.sample_item.sample_item_name}', please wait.",
        "process_id": process_id,
    }
