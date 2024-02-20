from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from ..controllers.sample_batches_controller import (
    get_sample_batches,
    get_sample_batch,
    get_batch_targets,
    create_sample_batch,
    delete_sample_batch,
    update_sample_batch,
    autosampler_import_batch,
    copy_sample_batch,
    sample_batch_export_peaks,
)
from ..models.pydantic_models.sample_pydantic_model import AlarmsList
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchCreate,
    SampleBatchUpdateBody,
    autoSamplerImportBatchData,
    SampleBatchCopyBody,
    SampleBatchExportPeaks,
)
from ..exceptions import ApiException

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
async def get_sample_batch_route(
    sample_batch_id: str,
):
    return await get_sample_batch(sample_batch_id)


@sample_batches_router.post("/api/sample_batches/{sample_batch_id}/targets")
async def get_batch_targets_route(sample_batch_id: str, body: AlarmsList):
    return await get_batch_targets(
        sample_batch_id,
        body.alarms_list,
    )


@sample_batches_router.post("/api/sample_batches")
async def create_sample_batch_route(sample_batch: SampleBatchCreate):
    return await create_sample_batch(sample_batch)


@sample_batches_router.delete("/api/sample_batches/{sample_batch_id}")
async def delete_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(delete_sample_batch, sample_batch_id, sid)
    return {"status": f"The sample batch (ID '{sample_batch_id}') deletion has started"}


@sample_batches_router.patch("/api/sample_batches/{sample_batch_id}")
async def update_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchUpdateBody,
    background_tasks: BackgroundTasks,
):
    try:
        sid = request.headers.get("X-SID")
        result = await update_sample_batch(sample_batch_id, body, background_tasks)
        # Convert the updated_sample_batch object to a JSON-serializable format
        result_data = jsonable_encoder(result)
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Sample batch '{body.sample_batch_name}' was successfully updated.",
                "data": result_data,
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@sample_batches_router.post("/api/sample_batches/import_batch")
async def autosampler_import_batch_route(
    data: autoSamplerImportBatchData,
    background_tasks: BackgroundTasks,
):
    return await autosampler_import_batch(
        data.sample_batch, data.sample_items, data.params, background_tasks
    )


@sample_batches_router.post("/api/sample_batches/{sample_batch_id}/copy")
async def copy_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchCopyBody,
    background_tasks: BackgroundTasks,
):
    try:
        sid = request.headers.get("X-SID")
        background_tasks.add_task(
            copy_sample_batch,
            sample_batch_id,
            body.workspace_id,
            body.sample_batch_name,
            body.sample_batch_description,
            sid,
        )
        return JSONResponse(
            status_code=200,
            content={
                "message": f"The copying process for '{body.sample_batch_name}' has started",
            },
        )
    # TODO_error_handling
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@sample_batches_router.post("/api/sample_batches/export_peaks")
async def sample_batch_export_peaks_route(
    request: Request,
    sample_batch: SampleBatchExportPeaks,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(sample_batch_export_peaks, sample_batch, sid)
    return {
        "status": f"The export peaks process for batch '{sample_batch.sample_batch_name}' has started"
    }
