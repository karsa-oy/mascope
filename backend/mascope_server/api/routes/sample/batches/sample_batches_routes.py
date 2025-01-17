from fastapi import APIRouter, BackgroundTasks, Request, Depends
from mascope_server.db.id import gen_id
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.auth.dependencies import editor_user, guest_user
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
from mascope_server.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreateBody,
    SampleBatchUpdateBody,
    GetSampleBatchesQueryParams,
    GetSampleBatchTargetsQueryParams,
    SampleBatchImportSamplesBody,
    SampleBatchCopyBody,
)
from mascope_server.api.new.instrument_configs.service import get_instrument_config

sample_batches_router = APIRouter(prefix="/api/sample/batches", tags=["Sample Batches"])


@sample_batches_router.get("")
@api_route(token_access=True)
async def get_sample_batches_route(
    query_params: GetSampleBatchesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of sample batches.

    :param query_params: Query parameters for sorting, filtering, and pagination.
    :type query_params: GetSampleBatchesQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of sample batches.
    :rtype: dict
    """
    return await get_sample_batches(**query_params.model_dump())


@sample_batches_router.get("/{sample_batch_id}")
@api_route()
async def get_sample_batch_route(
    sample_batch_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific sample batch by ID.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the sample batch details.
    :rtype: dict
    """
    return await get_sample_batch(sample_batch_id)


@sample_batches_router.get("/{sample_batch_id}/targets")
@api_route()
async def get_batch_targets_route(
    sample_batch_id: str,
    query_params: GetSampleBatchTargetsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve all targets associated with a specific sample batch.

    :param sample_batch_id: ID of the sample batch for which targets are being retrieved.
    :type sample_batch_id: str
    :param query_params: Query parameters for deduplication and pagination.
    :type query_params: GetSampleBatchTargetsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the target collections, compounds, ions, and isotopes.
    :rtype: dict
    """
    return await get_batch_targets(sample_batch_id, **query_params.model_dump())


@sample_batches_router.post("")
@api_route(status_code=201)
async def create_sample_batch_route(
    body: SampleBatchCreateBody,
    user=Depends(editor_user),
):
    """Create a new sample batch.

    :param body: The data required to create a sample batch.
    :type body: SampleBatchCreateBody
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing the newly created sample batch's details.
    :rtype: dict
    """
    return await create_sample_batch(sample_batch=body, independent_transaction=True)


@sample_batches_router.patch("/{sample_batch_id}")
@api_route()
async def update_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchUpdateBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Update details of an existing sample batch.

    :param sample_batch_id: The unique identifier of the sample batch to be updated.
    :type sample_batch_id: str
    :param body: The update data for the sample batch.
    :type body: SampleBatchUpdateBody
    :param background_tasks: Background task handler.
    :type background_tasks: BackgroundTasks
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing the updated sample batch details and a process ID.
    :rtype: dict
    """
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
        "message": result["message"],
        "data": result["data"],
        "process_id": process_id,
    }


@sample_batches_router.delete("/{sample_batch_id}")
@api_route(status_code=202)
async def delete_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Delete a specific sample batch by ID.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param background_tasks: Background task handler.
    :type background_tasks: BackgroundTasks
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing a message and process ID.
    :rtype: dict
    """
    # Fetch sample batch to have access to workspace_id and verify sample batch existence
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
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


@sample_batches_router.post("/{sample_batch_id}/import")
@api_route(status_code=202)
async def import_sample_items_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchImportSamplesBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Import sample items into a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param body: Data for importing sample items.
    :type body: SampleBatchImportSamplesBody
    :param background_tasks: Background task handler.
    :type background_tasks: BackgroundTasks
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing a message and process ID.
    :rtype: dict
    """
    # Ensure that sample_batch_id in path matches sample_batch_id in sample_items
    if any(si.sample_batch_id != sample_batch_id for si in body.sample_items):
        raise ValueError("The sample_batch_id in the route and sample_items must match")

    # Verify instrument config exists
    if body.instrument_config.instrument_function_id:
        instrument_config_record = await get_instrument_config(
            instrument_function_id=body.instrument_config.instrument_function_id
        )
        if not instrument_config_record:
            raise NotFoundException(
                "import sample items: no record found with instrument_function_id "
                + body.instrument_config.instrument_function_id
            )

    # Verify the existance of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        import_sample_items,
        sample_batch_id=sample_batch_id,
        sample_items=body.sample_items,
        mz_calibration_params=body.mz_calibration_params,
        instrument_config=body.instrument_config,
        calibrate_batch=body.calibrate_batch,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Importing {len(body.sample_items)} samples to the sample batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@sample_batches_router.post("/{sample_batch_id}/copy")
@api_route(status_code=202)
async def copy_sample_batch_route(
    request: Request,
    sample_batch_id: str,
    body: SampleBatchCopyBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Copy an existing sample batch to a new workspace.

    :param sample_batch_id: The unique identifier of the sample batch to copy.
    :type sample_batch_id: str
    :param body: Data required to copy the sample batch.
    :type body: SampleBatchCopyBody
    :param background_tasks: Background task handler.
    :type background_tasks: BackgroundTasks
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing a message and process ID.
    :rtype: dict
    """
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


@sample_batches_router.get("/{sample_batch_id}/export_peaks")
@api_route(status_code=202)
async def sample_batch_export_peaks_route(
    request: Request,
    sample_batch_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Export peak data for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param background_tasks: Background task handler.
    :type background_tasks: BackgroundTasks
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing a message and process ID.
    :rtype: dict
    """
    # Verify the existance of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
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
