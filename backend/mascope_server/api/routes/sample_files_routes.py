from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, timezone
from ..utils.api_features import api_route

from ..controllers.sample_files_controller import (
    get_sample_files,
    get_sample_file,
    create_sample_file,
    delete_sample_file,
    update_sample_file,
    get_sample_file_peaks,
    compute_all_sample_file_peaks,
    get_sample_file_peak_timeseries,
    get_sample_file_spectrum,
)
from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileCreate,
    SampleFileUpdate,
    GetSampleFilesQueryParams,
    GetRecentSampleFilesQueryParams,
    GetSampleFilePeakTimeseriesBody,
    GetSpectrumQueryParams,
)

sample_files_router = APIRouter()


@sample_files_router.get("/api/sample_files")
@api_route()
async def get_sample_files_route(query_params: GetSampleFilesQueryParams = Depends()):
    return await get_sample_files(**query_params.model_dump())


@sample_files_router.get("/api/sample_files/recent")
@api_route()
async def get_recent_sample_files_route(
    query_params: GetRecentSampleFilesQueryParams = Depends(),
):
    # Used datetime.now() with timezone.utc to get a timezone-aware UTC datetime
    datetime_min = datetime.now(timezone.utc) - timedelta(days=query_params.days)
    datetime_max = datetime.now(timezone.utc)

    query_params_dict = query_params.dict(exclude={"days"})
    # Update the dictionary with calculated datetime_min and datetime_max
    query_params_dict.update(
        {
            "datetime_min": datetime_min,
            "datetime_max": datetime_max,
        }
    )

    return await get_sample_files(**query_params_dict)


@sample_files_router.get("/api/sample_files/{sample_file_id}")
@api_route()
async def get_sample_file_route(sample_file_id: str):
    return await get_sample_file(sample_file_id)


@sample_files_router.post("/api/sample_files")
@api_route(
    status_code=201,
    include_message=True,
    success_message="Sample file created successfully",
)
async def create_sample_file_route(sample_file: SampleFileCreate):
    return await create_sample_file(sample_file)


@sample_files_router.patch("/api/sample_files/{sample_file_id}")
@api_route(include_message=True, success_message="Sample file updated successfully")
async def update_sample_file_route(sample_file_id: str, sample_file: SampleFileUpdate):
    return await update_sample_file(sample_file_id, sample_file)


@sample_files_router.delete("/api/sample_files/{sample_file_id}")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Sample file deleted successfully",
)
async def delete_sample_file_route(sample_file_id: str):
    await delete_sample_file(sample_file_id)


@sample_files_router.get("/api/sample_files/{sample_file_id}/peaks")
@api_route()
async def get_sample_file_peaks_route(sample_file_id: str):
    return await get_sample_file_peaks(sample_file_id)


@sample_files_router.get(
    "/api/sample_files/{sample_file_id}/peaks/compute", tags=["Sample File Peaks"]
)
@api_route(
    status_code=202,
)
async def compute_all_sample_file_peaks_route(
    request: Request,
    sample_file_id: str,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample file
    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]

    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        compute_all_sample_file_peaks,
        sample_file_id=sample_file_id,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Computina all peaks data for sample file '{filename}', please wait.",
        "process_id": process_id,
    }
@api_route()
async def get_sample_file_peak_timeseries_route(
    sample_file_id: str, body: GetSampleFilePeakTimeseriesBody
):
    return await get_sample_file_peak_timeseries(
        sample_file_id=sample_file_id,
        peak_mz=body.peak_mz,
        peak_mz_tolerance_ppm=body.peak_mz_tolerance_ppm,
    )


@sample_files_router.get("/api/sample_files/{sample_file_id}/spectrum")
@api_route()
async def get_sample_file_spectrum_route(
    sample_file_id: str,
    query_params: GetSpectrumQueryParams = Depends(),
):
    return await get_sample_file_spectrum(sample_file_id, **query_params.model_dump())
