from fastapi import APIRouter, BackgroundTasks

from ..controllers.sample_batches_controller import (
    get_sample_batch_by_id,
    get_sample_batches,
    create_sample_batch,
    delete_sample_batch,
    update_sample_batch,
    autosampler_import_batch,
    copy_sample_batch,
)
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchCreate,
    SampleBatchUpdate,
    autoSamplerImportBatchData,
    SampleBatchCopy,
)

sample_batches_router = APIRouter()


@sample_batches_router.get("/api/sample_batches")
async def get_sample_batches_route(
    workspace_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_sample_batches(workspace_id, sort, order, page, limit)


@sample_batches_router.get("/api/sample_batches/{sample_batch_id}")
async def get_sample_batch_by_id_route(sample_batch_id: str):
    return await get_sample_batch_by_id(sample_batch_id)


@sample_batches_router.post("/api/sample_batches")
async def create_sample_batch_route(sample_batch: SampleBatchCreate):
    return await create_sample_batch(sample_batch)


@sample_batches_router.delete("/api/sample_batches/{sample_batch_id}")
async def delete_sample_batch_route(
    sample_batch_id: str, background_tasks: BackgroundTasks
):
    background_tasks.add_task(delete_sample_batch, sample_batch_id)
    return {"status": f"The sample batch (ID '{sample_batch_id}') deletion has started"}


@sample_batches_router.patch("/api/sample_batches/{sample_batch_id}")
async def update_sample_batch_route(
    sample_batch_id: str,
    sample_batch: SampleBatchUpdate,
    background_tasks: BackgroundTasks,
):
    return await update_sample_batch(sample_batch_id, sample_batch, background_tasks)


@sample_batches_router.post("/api/sample_batches/import_batch")
async def autosampler_import_batch_route(
    data: autoSamplerImportBatchData,
    background_tasks: BackgroundTasks,
):
    return await autosampler_import_batch(
        data.sample_batch, data.sample_items, data.params, background_tasks
    )


@sample_batches_router.post("/api/sample_batches/copy")
async def copy_sample_batch_route(
    sample_batch_copy: SampleBatchCopy, background_tasks: BackgroundTasks
):
    background_tasks.add_task(copy_sample_batch, sample_batch_copy)
    return {
        "status": f"The copying process for '{sample_batch_copy.sample_batch_name}' has started"
    }
