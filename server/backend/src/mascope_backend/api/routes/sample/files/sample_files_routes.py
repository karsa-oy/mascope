import os
import shutil

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Request, Depends, UploadFile
from typing import Callable

from tuspyserver import create_tus_router

from mascope_backend.api.new.auth.access_token.service import get_access_token
from mascope_backend.db.id import gen_id
from mascope_backend.api.new.auth.dependencies import guest_user, editor_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.sample.files.process.service import (
    auto_process_sample_file,
)
from mascope_backend.api.controllers.sample.files.sample_files_controller import (
    get_sample_files,
    get_sample_file,
    create_sample_file,
    delete_sample_file,
    delete_sample_files,
    update_sample_file,
    upload_sample_file,
    get_sample_file_peaks,
    compute_sample_file_peaks,
    get_sample_file_peak_timeseries,
    get_sample_file_spectrum,
    get_sample_file_metadata,
)
from mascope_backend.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileCreate,
    SampleFileUpdate,
    GetSampleFilesQueryParams,
    GetRecentSampleFilesQueryParams,
    GetSampleFilePeaksQueryParams,
    ComputeSampleFilePeaksQueryParams,
    GetSampleFilePeakTimeseriesBody,
    GetSpectrumQueryParams,
    DeleteSampleFilesBody,
)

from mascope_backend.runtime import runtime

sample_files_router = APIRouter(prefix="/api/sample/files", tags=["Sample Files"])


@sample_files_router.get("")
@api_route(token_access=True)
async def get_sample_files_route(
    query_params: GetSampleFilesQueryParams = Depends(), user=Depends(guest_user)
):
    """Retrieve a list of sample files with optional filtering and pagination.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :param user: Authenticated user with guest access.
    :return: A dictionary with total count and list of sample files.
    """
    return await get_sample_files(**query_params.model_dump())


@sample_files_router.get("/recent")
@api_route()
async def get_recent_sample_files_route(
    query_params: GetRecentSampleFilesQueryParams = Depends(), user=Depends(guest_user)
):
    """Retrieve recent sample files within a specified date range.

    :param query_params: Query parameters including date range in days.
    :param user: Authenticated user with guest access.
    :return: A dictionary with recent sample files matching criteria.
    """
    datetime_min = datetime.now(timezone.utc) - timedelta(days=query_params.days)
    query_params_dict = query_params.model_dump(exclude={"days"})
    # Update the dictionary with calculated datetime_min
    query_params_dict.update(
        {
            "datetime_min": datetime_min,
        }
    )

    return await get_sample_files(**query_params_dict)


@sample_files_router.get("/{sample_file_id}")
@api_route()
async def get_sample_file_route(sample_file_id: str, user=Depends(guest_user)):
    """Retrieve details of a specific sample file by ID.

    :param sample_file_id: ID of the sample file to retrieve.
    :param user: Authenticated user with guest access.
    :return: Details of the specified sample file.
    """
    return await get_sample_file(sample_file_id)


@sample_files_router.post("")
@api_route(status_code=201, token_access=True)
async def create_sample_file_route(
    request: Request,
    sample_file_create: SampleFileCreate,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Create a new sample file record.

    :param request: The request object.
    :param sample_file_create: Data required for creating a sample file.
    :param background_tasks: Background tasks for triggering an automatic processing for sample file after creation.
    :param user: Authenticated user with editor access.
    :return: The created sample file's details.
    """
    return await create_sample_file(
        sample_file_create=sample_file_create,
        background_tasks=background_tasks,
        sid=request.headers.get("X-SID"),
        process_id=gen_id(8),
    )


@sample_files_router.patch("/{sample_file_id}")
@api_route()
async def update_sample_file_route(
    sample_file_id: str, sample_file: SampleFileUpdate, user=Depends(editor_user)
):
    """Update details of an existing sample file.

    :param sample_file_id: ID of the sample file to update.
    :param sample_file: Data for updating the sample file.
    :param user: Authenticated user with editor access.
    :return: Updated details of the sample file.
    """
    return await update_sample_file(sample_file_id, sample_file)


@sample_files_router.delete("/{sample_file_id}")
@api_route()
async def delete_sample_file_route(sample_file_id: str, user=Depends(editor_user)):
    """Delete a specific sample file by ID.

    :param sample_file_id: ID of the sample file to delete.
    :param user: Authenticated user with editor access.
    :return: Confirmation message on deletion.
    """
    await delete_sample_file(sample_file_id)


@sample_files_router.post("/delete")
@api_route(token_access=True)
async def delete_sample_files_route(
    body: DeleteSampleFilesBody, user=Depends(editor_user)
):
    """Delete multiple sample files by their IDs or filenames.

    Only deletes files that don't have existing sample items associated with them.
    Returns information about which files were deleted and which were skipped.

    :param body: Request body containing either list of sample file IDs or filenames to delete.
    :param user: Authenticated user with editor access.
    :return: Information about deleted and skipped files.
    """
    return await delete_sample_files(**body.model_dump())


@sample_files_router.get("/{sample_file_id}/peaks")
@api_route(token_access=True)
async def get_sample_file_peaks_route(
    sample_file_id: str,
    query_params: GetSampleFilePeaksQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve peaks for a specific sample file.

    :param sample_file_id: ID of the sample file.
    :param query_params: Parameters for retrieving peaks.
    :param user: Authenticated user with guest access.
    :return: Peak data for the sample file.
    """
    return await get_sample_file_peaks(sample_file_id, **query_params.model_dump())


@sample_files_router.get("/{sample_file_id}/peaks/compute")
@api_route(status_code=202)
async def compute_sample_file_peaks_route(
    request: Request,
    sample_file_id: str,
    background_tasks: BackgroundTasks,
    query_params: ComputeSampleFilePeaksQueryParams = Depends(),
    user=Depends(editor_user),
):
    """Compute all peaks for a sample file asynchronously.

    :param sample_file_id: ID of the sample file to compute peaks for.
    :param request: The request object.
    :param background_tasks: FastAPI background task manager.
    :param user: Authenticated user with editor access.
    :return: Process initiation message.
    """
    # Verify the existance of sample file
    sample_file_data = await get_sample_file(sample_file_id)
    filename = sample_file_data.get("data").get("filename")

    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        compute_sample_file_peaks,
        sample_file_id=sample_file_id,
        if_exists=query_params.if_exists,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Computing all peaks data for sample file '{filename}', please wait.",
        "process_id": process_id,
    }


@sample_files_router.post("/{sample_file_id}/peaks/timeseries")
@api_route(token_access=True)
async def get_sample_file_peak_timeseries_route(
    sample_file_id: str, body: GetSampleFilePeakTimeseriesBody, user=Depends(guest_user)
):
    """Retrieve timeseries for a specific peak in a sample file.

    :param sample_file_id: ID of the sample file.
    :param body: Data including peak m/z and tolerance.
    :param user: Authenticated user with guest access.
    :return: Timeseries data for the specified peak.
    """
    return await get_sample_file_peak_timeseries(
        sample_file_id=sample_file_id,
        peak_mz=body.peak_mz,
        peak_mz_tolerance_ppm=body.peak_mz_tolerance_ppm,
    )


@sample_files_router.get("/{sample_file_id}/spectrum")
@api_route(token_access=True)
async def get_sample_file_spectrum_route(
    sample_file_id: str,
    query_params: GetSpectrumQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve spectrum data for a sample file within a specific range.

    :param sample_file_id: ID of the sample file.
    :param query_params: Parameters for spectrum range.
    :param user: Authenticated user with guest access.
    :return: Spectrum data for the sample file.
    """
    return await get_sample_file_spectrum(sample_file_id, **query_params.model_dump())


@sample_files_router.get("/{sample_file_id}/metadata")
@api_route(token_access=True)
async def get_sample_file_metadata_route(
    sample_file_id: str,
    user=Depends(guest_user),
):
    """
    Retrieve metadata for a specific sample file.

    :param sample_file_id: ID of the sample file.
    :param user: Authenticated user with guest access.
    :return: Metadata for the sample file.
    """
    return await get_sample_file_metadata(sample_file_id)


@sample_files_router.post("/{sample_file_id}/process")
@api_route(status_code=202)
async def process_sample_item_route(
    sample_file_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Process a sample item, including creation, calibration, and matching.

    :param body: The data for processing the sample item.
    :param background_tasks: Background tasks for processing the item.
    :param user: The current authenticated user with editor permissions.
    :return: A dictionary confirming the processing has started.
    """
    # Verify the existence of sample file
    sample_file = (await get_sample_file(sample_file_id)).get("data")

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        auto_process_sample_file,
        sample_file_id=sample_file_id,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )

    return {
        "message": f"Processing sample file '{sample_file.get('filename')}', please wait.",
        "process_id": process_id,
    }


def get_upload_handler(
    request: Request,
    user=Depends(editor_user),
) -> Callable[[str, dict], None]:
    """Get the upload handler for processing file uploads.

    :param request: The HTTP request object.
    :type request: Request
    :param user: The current authenticated user with editor permissions.
    :type user: _type_, optional
    :return: A callable that handles the file upload.
    :rtype: Callable[[str, dict], None]
    """

    async def handler(file_path: str, metadata: dict):
        # Rename file from temporary name back to original
        dest_path = os.path.join(os.path.dirname(file_path), metadata["filename"])
        shutil.copyfile(file_path, dest_path)
        # Extract user session ID from headers
        sid = request.headers.get("X-SID")
        # Single token validation for the entire upload process
        access_token = await get_access_token(user=user, service_name="file-converter")
        # Process the uploaded file
        await upload_sample_file(
            dest_path,
            user=user,
            access_token=access_token,
            sid=sid,
        )

    return handler


sample_files_upload_router = create_tus_router(
    files_dir=runtime.env.path("temp"),
    upload_complete_dep=get_upload_handler,
    prefix="api/sample/files/upload",
)
