from fastapi import APIRouter
from datetime import datetime, timedelta

from ..controllers.sample_files_controller import (
    get_sample_files,
    get_sample_file_by_id,
    get_mz_calibration,
)

sample_files_router = APIRouter()


@sample_files_router.get("/api/sample_files")
async def get_sample_files_route(
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
    minDatetime: datetime = None,
    maxDatetime: datetime = None,
    instrument: str = None,
):
    return await get_sample_files(
        sort, order, page, limit, minDatetime, maxDatetime, instrument
    )


@sample_files_router.get("/api/sample_files/recent")
async def get_recent_sample_files_route(
    instrument: str,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    minDatetime = datetime.utcnow() - timedelta(days=1)
    maxDatetime = datetime.utcnow()
    print(datetime.now())
    print(minDatetime)
    print(maxDatetime)
    return await get_sample_files(
        sort, order, page, limit, minDatetime, maxDatetime, instrument
    )


@sample_files_router.get("/api/sample_files/mz_calibration")
async def get_last_mz_calibration_route(
    instrument: str,
):
    return await get_mz_calibration(instrument)


@sample_files_router.get("/api/sample_files/{sample_file_id}")
async def get_sample_file_by_id_route(sample_file_id: str):
    return await get_sample_file_by_id(sample_file_id)
