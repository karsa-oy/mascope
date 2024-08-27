from fastapi import APIRouter, BackgroundTasks, Request, Depends
from mascope_server.db.id import gen_id
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.sample.batches.sample_batches_controller import (
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
from mascope_server.api.models.samples.sample_pydantic_model import AlarmsList
from mascope_server.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreateBody,
    SampleBatchUpdateBody,
    GetSampleBatchesQueryParams,
    SampleBatchImportSamplesBody,
    SampleBatchCopyBody,
)

sample_batches_router = APIRouter()


@sample_batches_router.get("/api/sample/batches")
@api_route()
async def get_sample_batches_route(
    query_params: GetSampleBatchesQueryParams = Depends(),
):
    return await get_sample_batches(**query_params.model_dump())


@sample_batches_router.get("/api/sample/batches/{sample_batch_id}")
@api_route()
async def get_sample_batch_route(
    sample_batch_id: str,
):
    return await get_sample_batch(sample_batch_id)


@sample_batches_router.post("/api/sample/batches/{sample_batch_id}/targets")
@api_route(
    include_message=True,
    success_message="Sample batch targets fetched successfully",
)
async def get_batch_targets_route(sample_batch_id: str, body: AlarmsList):
    return await get_batch_targets(
        sample_batch_id,
        body.alarms_list,
    )


@sample_batches_router.post("/api/sample/batches")
@api_route(
    status_code=201,
)
async def create_sample_batch_route(body: SampleBatchCreateBody):
    return await create_sample_batch(sample_batch=body, independent_transaction=True)


@sample_batches_router.patch("/api/sample/batches/{sample_batch_id}")
@api_route()
async def update_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchUpdateBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    # generate process_id for the background task ramatch_batches
    process_id = gen_id(8)

    result = await update_sample_batch(
        sample_batch_id=sample_batch_id,
        sample_batch_update_body=body,
        background_tasks=background_tasks,
        sid=sid,
        process_id=process_id,
    )

    return {
        "data": result["data"],
        "message": result["message"],
        "process_id": process_id,
    }


@sample_batches_router.delete("/api/sample/batches/{sample_batch_id}")
@api_route(
    status_code=202,
)
async def delete_sample_batch_route(
    request: Request, sample_batch_id: str, background_tasks: BackgroundTasks
):
    # Fetch sample batch to have access to workspace_id and verify sample batch existence
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        delete_sample_batch,
        sample_batch_id=sample_batch_id,
        workspace_id=sample_batch["workspace_id"],
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )

    return {
        "message": f"Deleting batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@sample_batches_router.post("/api/sample/batches/{sample_batch_id}/import")
@api_route(
    status_code=202,
)
async def import_sample_items_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchImportSamplesBody,
    background_tasks: BackgroundTasks,
):
    # Ensure that sample_batch_id in path matches sample_batch_id in sample_items
    if any(si.sample_batch_id != sample_batch_id for si in body.sample_items):
        raise ValueError("The sample_batch_id in the route and sample_items must match")

    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        import_sample_items,
        sample_batch_id=sample_batch_id,
        sample_items=body.sample_items,
        mz_calibration_params=body.mz_calibration_params,
        calibrate_batch=body.calibrate_batch,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Importing {len(body.sample_items)} samples to the sample batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@sample_batches_router.post("/api/sample/batches/{sample_batch_id}/copy")
@api_route(
    status_code=202,
)
async def copy_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchCopyBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        copy_sample_batch,
        sample_batch_id=sample_batch_id,
        workspace_id=body.workspace_id,
        sample_batch_name=body.sample_batch_name,
        sample_batch_description=body.sample_batch_description,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Copying batch '{body.sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@sample_batches_router.get("/api/sample/batches/{sample_batch_id}/export_peaks")
@api_route(
    status_code=202,
)
async def sample_batch_export_peaks_route(
    request: Request,
    sample_batch_id: str,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        sample_batch_export_peaks,
        sample_batch_id=sample_batch_id,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Exporting peak data for batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }
