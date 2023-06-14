from fastapi import APIRouter
from datetime import datetime, timedelta

from ..controllers.sample_files_controller import (
    get_sample_files,
    get_sample_file_by_id,
    create_sample_file,
    delete_sample_file,
    update_sample_file,
)
from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileCreate,
    SampleFileUpdate,
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
    filename: str = None,
):
    return await get_sample_files(
        sort, order, page, limit, minDatetime, maxDatetime, instrument, filename
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

    return await get_sample_files(
        sort, order, page, limit, minDatetime, maxDatetime, instrument
    )


@sample_files_router.get("/api/sample_files/{sample_file_id}")
async def get_sample_file_by_id_route(sample_file_id: str):
    return await get_sample_file_by_id(sample_file_id)


@sample_files_router.post("/api/sample_files")
async def create_sample_file_route(sample_file: SampleFileCreate):
    return await create_sample_file(sample_file)


@sample_files_router.delete("/api/sample_files/{sample_file_id}")
async def delete_sample_file_route(sample_file_id: str):
    return await delete_sample_file(sample_file_id)


@sample_files_router.patch("/api/sample_files/{sample_file_id}")
async def update_sample_file_route(sample_file_id: str, sample_file: SampleFileUpdate):
    return await update_sample_file(sample_file_id, sample_file)
