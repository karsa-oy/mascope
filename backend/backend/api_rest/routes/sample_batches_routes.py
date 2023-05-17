from fastapi import APIRouter
from ..controllers.sample_batches_controller import (
    get_sample_batches,
    get_sample_batch_by_id,
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
