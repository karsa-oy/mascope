from fastapi import APIRouter, BackgroundTasks, Request, Depends
from ..utils.api_features import api_route
from ..controllers.sample_batches_controller import (
    get_sample_batches,
    get_sample_batch,
    get_batch_targets,
    create_sample_batch,
    delete_sample_batch,
    update_sample_batch,
    import_sample_items,
    copy_sample_batch,
    sample_batch_export_peaks,
)
from ..models.pydantic_models.sample_pydantic_model import AlarmsList
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchCreateBody,
    SampleBatchUpdateBody,
    GetSampleBatchesQueryParams,
    SampleBatchImportSamplesBody,
    SampleBatchCopyBody,
    SampleBatchExportPeaks,
)

sample_batches_router = APIRouter()


@sample_batches_router.get("/api/sample_batches")
@api_route()
async def get_sample_batches_route(
    query_params: GetSampleBatchesQueryParams = Depends(),
):
    return await get_sample_batches(**query_params.dict())


@sample_batches_router.get("/api/sample_batches/{sample_batch_id}")
@api_route()
async def get_sample_batch_route(
    sample_batch_id: str,
):
    return await get_sample_batch(sample_batch_id)


@sample_batches_router.post("/api/sample_batches/{sample_batch_id}/targets")
@api_route(
    include_message=True,
    success_message="Sample batch targets fetched successfully",
)
async def get_batch_targets_route(sample_batch_id: str, body: AlarmsList):
    return await get_batch_targets(
        sample_batch_id,
        body.alarms_list,
    )


@sample_batches_router.post("/api/sample_batches")
@api_route(
    status_code_success=201,
    include_message=True,
    success_message="Sample batch created successfully",
)
async def create_sample_batch_route(body: SampleBatchCreateBody):
    return await create_sample_batch(sample_batch=body, independent_transaction=True)


@sample_batches_router.patch("/api/sample_batches/{sample_batch_id}")
@api_route(include_message=True, success_message="Sample batch updated successfully")
async def update_sample_batch_route(
    sample_batch_id: str,
    body: SampleBatchUpdateBody,
    background_tasks: BackgroundTasks,
):
    return await update_sample_batch(
        sample_batch_id=sample_batch_id,
        sample_batch_update_body=body,
        background_tasks=background_tasks,
    )


@sample_batches_router.delete("/api/sample_batches/{sample_batch_id}")
@api_route(
    include_data=False,
    include_message=True,
    success_message="The sample batch deletion has started",
)
async def delete_sample_batch_route(
    request: Request, sample_batch_id: str, background_tasks: BackgroundTasks
):
    sid = request.headers.get("X-SID")
    # Fetch sample batch to have access to workspace_id and verify sample batch existence
    sample_batch = await get_sample_batch(sample_batch_id)
    background_tasks.add_task(
        delete_sample_batch,
        sample_batch_id=sample_batch_id,
        workspace_id=sample_batch["workspace_id"],
        independent_transaction=True,
        sid=sid,
    )


@sample_batches_router.post("/api/sample_batches/{sample_batch_id}/import")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Importing samples to the sample batch has started",
)
async def import_sample_items_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchImportSamplesBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")

    # Ensure that sample_batch_id in path matches sample_batch_id in sample_items
    if any(si.sample_batch_id != sample_batch_id for si in body.sample_items):
        raise ValueError("The sample_batch_id in the route and sample_items must match")

    # Verify the existance of sample batch
    await get_sample_batch(sample_batch_id)

    background_tasks.add_task(
        import_sample_items,
        sample_batch_id=sample_batch_id,
        sample_items=body.sample_items,
        params=body.params,
        calibrate_batch=body.calibrate_batch,
        independent_transaction=True,
        sid=sid,
    )


@sample_batches_router.post("/api/sample_batches/{sample_batch_id}/copy")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Copying sample batch has started",
)
async def copy_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchCopyBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(
        copy_sample_batch,
        sample_batch_id=sample_batch_id,
        workspace_id=body.workspace_id,
        sample_batch_name=body.sample_batch_name,
        sample_batch_description=body.sample_batch_description,
        independent_transaction=True,
        sid=sid,
    )


@sample_batches_router.post("/api/sample_batches/export_peaks")
@api_route(
    include_data=False,
    include_message=True,
    success_message="The export peaks process for batch has started",
)
async def sample_batch_export_peaks_route(
    request: Request,
    sample_batch: SampleBatchExportPeaks,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(
        sample_batch_export_peaks,
        sample_batch=sample_batch,
        independent_transaction=True,
        sid=sid,
    )
